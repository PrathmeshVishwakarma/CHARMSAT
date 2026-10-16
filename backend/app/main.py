import time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from app.models.domain import Signal, Cable, AllocatedSlot, AllocResult, Violation, TQ, RevisionSummary
from app.models.rules import RuleSetConfig, GenericRuleConfig
from app.engine.generator import SyntheticGenerator
from app.engine.mapper import ColumnAutoMapper, ColumnMappingResult
from app.engine.validator import DataValidator
from app.engine.solver import CharmsatSolver
from app.engine.checker import IndependentChecker
from app.engine.baselines import BaselineEngine
from app.engine.naming import NameGenerator
from app.engine.excel_io import ExcelIO
from app.engine.storage import StorageEngine
from app.engine.rule_assistant import RuleAssistant

from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(
    title="CHARMSAT Engine API",
    description="Rule-driven DeltaV IO Signal Sudoku allocation engine with CP-SAT and independent verification",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = StorageEngine()
current_rules = RuleSetConfig()

# In-memory session state for demo
session_state: Dict[str, Any] = {
    "signals_a": [],
    "cables_info_a": [],
    "alloc_a": None,
    "signals_b": [],
    "alloc_b": None,
}

class GenerateRequest(BaseModel):
    n_signals: int = 1000
    seed: int = 42
    fuzz_headers: bool = False
    inject_defects: bool = False
    defect_types: Optional[List[str]] = None

class MapColumnsRequest(BaseModel):
    columns: List[str]

class ParseNLRuleRequest(BaseModel):
    text: str

class AllocateRequest(BaseModel):
    signals: Optional[List[Signal]] = None
    cable_sizes: Optional[Dict[str, int]] = None
    rules: Optional[RuleSetConfig] = None
    use_rev_a_as_hints: bool = False

def _moves_between(prev_allocs, new_allocs) -> int:
    """Measured moves: tags present in both allocations whose slot changed."""
    def pos(a):
        return (a.cabinet, a.cioc, a.baseplate, a.slot)
    prev = {a.tag: pos(a) for a in prev_allocs if a.tag}
    new = {a.tag: pos(a) for a in new_allocs if a.tag}
    return sum(1 for t, p in prev.items() if t in new and new[t] != p)

class PlantViolationRequest(BaseModel):
    plant_type: str = "ab_leak"  # 'ab_leak' | 'split_cable' | 'cross_boundary' | 'scatter_group'

class BenchmarkRequest(BaseModel):
    signal_count: int = 1000
    seed: int = 42

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "CHARMSAT", "engine": "OR-Tools CP-SAT", "independent_checker": "active"}

@app.get("/api/rules")
def get_rules():
    return {
        "rules": current_rules.model_dump(),
        "yaml": current_rules.to_yaml()
    }

@app.post("/api/rules")
def update_rules(payload: Dict[str, Any]):
    global current_rules
    if "yaml" in payload and payload["yaml"]:
        current_rules = RuleSetConfig.from_yaml(payload["yaml"])
    elif "rules" in payload:
        current_rules = RuleSetConfig.model_validate(payload["rules"])
    storage.save_rule_set("active", current_rules.to_yaml())
    return {
        "rules": current_rules.model_dump(),
        "yaml": current_rules.to_yaml()
    }

@app.post("/api/rules/parse-nl")
def parse_nl_rule(req: ParseNLRuleRequest):
    draft, msg = RuleAssistant.parse_natural_language_rule(req.text)
    return {
        "draft": draft.model_dump() if draft else None,
        "message": msg,
        "assistant_banner": "Rule Assistant is active for wording syntax only. AI never places signals."
    }

@app.post("/api/generate")
def generate_dataset(req: GenerateRequest):
    gen = SyntheticGenerator(seed=req.seed)
    signals, cables_info = gen.generate_dataset(
        n_signals=req.n_signals,
        inject_defects=req.inject_defects,
        defect_types=req.defect_types
    )
    df = gen.to_dataframe(signals, cables_info, fuzz_headers=req.fuzz_headers)

    # Save to session
    session_state["signals_a"] = signals
    session_state["cables_info_a"] = cables_info

    return {
        "signal_count": len(signals),
        "cable_count": len(cables_info),
        "columns": list(df.columns),
        "sample_rows": df.head(15).to_dict(orient="records"),
        "raw_signals": [s.__dict__ for s in signals[:200]],  # first 200 for preview
        "cable_sizes": {c["cable_id"]: c["size"] for c in cables_info}
    }

@app.post("/api/map-columns")
def map_columns(req: MapColumnsRequest):
    mapper = ColumnAutoMapper()
    result = mapper.map_columns(req.columns)
    return result.model_dump()

@app.post("/api/allocate")
def run_allocation(req: AllocateRequest):
    global current_rules
    rules_to_use = req.rules or current_rules

    # Use session signals if none provided
    signals = req.signals
    if not signals and session_state.get("signals_a"):
        signals = session_state["signals_a"]
    elif signals:
        # Convert Pydantic/dict to Signal dataclass if needed
        signals = [Signal(**s) if isinstance(s, dict) else s for s in signals]

    if not signals:
        raise HTTPException(status_code=400, detail="No signals provided for allocation")

    cable_sizes = req.cable_sizes or {}
    if not cable_sizes and session_state.get("cables_info_a"):
        cable_sizes = {c["cable_id"]: c["size"] for c in session_state["cables_info_a"]}

    # Step 1: Validate data and generate data TQs
    validator = DataValidator(spare_pct=rules_to_use.spare_capacity.spare_percentage)
    valid_signals, data_tqs = validator.validate(signals, cable_sizes)

    # Step 2: Solve with CP-SAT
    solver = CharmsatSolver(rules_to_use)
    prev_alloc = session_state.get("alloc_a").allocations if (req.use_rev_a_as_hints and session_state.get("alloc_a")) else None

    result = solver.solve(
        signals=valid_signals,
        cable_sizes=cable_sizes,
        prev_allocation=prev_alloc
    )

    # Merge data TQs with solver TQs
    result.tqs.extend(data_tqs)
    # Recalculate coverage
    total_in = len(signals)
    covered = len([s for s in result.allocations if not s.is_spare]) + sum(len(t.items) for t in result.tqs)
    result.coverage_pct = round(min(100.0, 100.0 * covered / max(1, total_in)), 1)

    if req.use_rev_a_as_hints:
        session_state["alloc_b"] = result
    else:
        session_state["alloc_a"] = result

    return result.model_dump()

@app.post("/api/checker/plant-violation")
def plant_violation(req: PlantViolationRequest):
    active_alloc = session_state.get("alloc_a")
    if not active_alloc or not active_alloc.allocations:
        raise HTTPException(status_code=400, detail="Run allocation first before planting a violation")

    checker = IndependentChecker(current_rules)
    tampered_allocations = checker.plant_violation(active_alloc.allocations, req.plant_type)
    violations = checker.verify(tampered_allocations)

    return {
        "status": "TAMPERED_FOR_AUDIT_DEMO",
        "plant_type": req.plant_type,
        "violations_detected_by_independent_checker": len(violations),
        "violations": [v.model_dump() for v in violations],
        "tampered_sample_slots": [s.model_dump() for s in tampered_allocations[:50]]
    }

@app.post("/api/revision/generate-b")
def generate_revision_b(add_pct: float = 0.05, del_pct: float = 0.02, type_pct: float = 0.015, recable_pct: float = 0.0):
    signals_a = session_state.get("signals_a")
    if not signals_a:
        gen = SyntheticGenerator(seed=42)
        signals_a, cab_info = gen.generate_dataset(n_signals=1000)
        session_state["signals_a"] = signals_a
        session_state["cables_info_a"] = cab_info

    cables_a = {c["cable_id"]: c["size"] for c in session_state.get("cables_info_a", [])} or None
    gen = SyntheticGenerator(seed=42)
    signals_b, diff_meta = gen.generate_revision_b(
        rev_a_signals=signals_a,
        add_pct=add_pct,
        del_pct=del_pct,
        type_change_pct=type_pct,
        recable_pct=recable_pct,
        cable_sizes=cables_a,
    )

    session_state["signals_b"] = signals_b

    # Allocate Rev B with min-move; Rev A cable sizes are carried, never inferred
    cable_sizes_b = diff_meta["cable_sizes"]
    solver = CharmsatSolver(current_rules)
    prev_alloc = session_state.get("alloc_a").allocations if session_state.get("alloc_a") else None

    result_b = solver.solve(
        signals=signals_b,
        cable_sizes=cable_sizes_b,
        prev_allocation=prev_alloc
    )
    session_state["alloc_b"] = result_b

    return {
        "diff_meta": diff_meta,
        "rev_b_result": result_b.model_dump()
    }

@app.post("/api/benchmark/run")
def run_benchmark(req: BenchmarkRequest):
    gen = SyntheticGenerator(seed=req.seed)
    signals, cables_info = gen.generate_dataset(n_signals=req.signal_count)
    cable_sizes = {c["cable_id"]: c["size"] for c in cables_info}

    # Generate Rev B for comparison (sizes carried from Rev A, never inferred)
    signals_b, diff_meta_b = gen.generate_revision_b(signals, cable_sizes=cable_sizes)
    cable_sizes_b = diff_meta_b["cable_sizes"]

    baselines = BaselineEngine(current_rules)
    solver = CharmsatSolver(current_rules)

    # 1. B0 Greedy in file order
    b0_res = baselines.run_b0_file_order(signals, cable_sizes)

    # 2. B1 Greedy grouped & A/B aware
    b1_res = baselines.run_b1_grouped_ab(signals, cable_sizes)

    # 3. CHARMSAT CP-SAT
    charmsat_res_a = solver.solve(signals, cable_sizes)
    # Solve Rev B
    charmsat_res_b = solver.solve(signals_b, cable_sizes_b, prev_allocation=charmsat_res_a.allocations)

    # Rev B moves for B1 (measured: re-run B1 on Rev B, count moved tags)
    b1_rev_b = baselines.run_b1_grouped_ab(signals_b, cable_sizes_b)
    b0_rev_b = baselines.run_b0_file_order(signals_b, cable_sizes_b)
    # Measured moves: compare each baseline's Rev A vs Rev B allocations tag-by-tag.
    b0_moves = _moves_between(b0_res.allocations, b0_rev_b.allocations)
    b1_moves = _moves_between(b1_res.allocations, b1_rev_b.allocations)
    charmsat_moves = charmsat_res_b.rev_summary.moves_ours if charmsat_res_b.rev_summary else 0

    lower_bound = max(1, (len(signals) + 344) // 345)

    def _verdict(name, viols, cabs, lb, status=""):
        if viols > 0:
            return "FAIL (Violates Rules)"
        if cabs == lb:
            return "OPTIMAL (matches lower bound)" if not status or status == "OPTIMAL" else f"FEASIBLE (matches lower bound, {status})"
        return f"GAP {cabs - lb} (uses {cabs}, lower bound {lb})"

    results = [
        {
            "engine": "B0 Greedy (File Order)",
            "violations": len(b0_res.violations),
            "cabinets": b0_res.cabinets_used,
            "cabinets_vs_lb": f"{b0_res.cabinets_used} / {lower_bound}",
            "rev_b_moves": b0_moves,
            "runtime_s": round(b0_res.runtime_s, 3),
            "verdict": _verdict("B0", len(b0_res.violations), b0_res.cabinets_used, lower_bound)
        },
        {
            "engine": "B1 Greedy (Grouped + A/B)",
            "violations": len(b1_res.violations),
            "cabinets": b1_res.cabinets_used,
            "cabinets_vs_lb": f"{b1_res.cabinets_used} / {lower_bound}",
            "rev_b_moves": b1_moves,
            "runtime_s": round(b1_res.runtime_s, 3),
            "verdict": _verdict("B1", len(b1_res.violations), b1_res.cabinets_used, lower_bound)
        },
        {
            "engine": "CHARMSAT (CP-SAT Solver)",
            "violations": len(charmsat_res_a.violations),
            "cabinets": charmsat_res_a.cabinets_used,
            "cabinets_vs_lb": f"{charmsat_res_a.cabinets_used} / {lower_bound}",
            "rev_b_moves": charmsat_moves,
            "runtime_s": round(charmsat_res_a.runtime_s, 3),
            "verdict": _verdict("CHARMSAT", len(charmsat_res_a.violations), charmsat_res_a.cabinets_used, lower_bound, charmsat_res_a.solver_status)
        }
    ]

    for r in results:
        storage.save_benchmark(
            run_name=f"Bench-{req.signal_count}",
            count=req.signal_count,
            engine=r["engine"],
            viols=r["violations"],
            cabs=r["cabinets"],
            lb=lower_bound,
            moves=r["rev_b_moves"],
            runtime=r["runtime_s"]
        )

    return {
        "signal_count": req.signal_count,
        "lower_bound_cabinets": lower_bound,
        "benchmark_table": results,
        # Only the point just measured. History across N comes from `make bench`
        # (bench/results.json), never from typed-in constants.
        "runtime_line_chart": [
            {"signals": req.signal_count, "b0": round(b0_res.runtime_s, 3),
             "b1": round(b1_res.runtime_s, 3), "charmsat": round(charmsat_res_a.runtime_s, 3)}
        ]
    }

@app.post("/api/export/excel")
def export_excel():
    active_alloc = session_state.get("alloc_a")
    if not active_alloc:
        raise HTTPException(status_code=400, detail="No active allocation to export")

    kpis = {
        "cabinets_used": active_alloc.cabinets_used,
        "lower_bound": active_alloc.lower_bound_cabinets,
        "spare_pct": active_alloc.spare_pct_actual,
        "runtime_s": active_alloc.runtime_s
    }

    excel_bytes = ExcelIO.export_workbook(
        allocations=active_alloc.allocations,
        violations=active_alloc.violations,
        tqs=active_alloc.tqs,
        rev_summary=session_state.get("alloc_b").rev_summary if session_state.get("alloc_b") else None,
        kpis=kpis
    )

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=CHARMSAT_DeltaV_IO_Allocation.xlsx"}
    )

@app.get("/api/demo-init")
def demo_init():
    """
    Initializes a complete seeded 1,000-signal run end-to-end,
    generating Rev A, allocating it with CP-SAT, generating Rev B,
    and verifying zero violations.
    """
    gen = SyntheticGenerator(seed=42)
    sig_a, cab_info_a = gen.generate_dataset(n_signals=1000)
    c_sizes_a = {c["cable_id"]: c["size"] for c in cab_info_a}
    session_state["signals_a"] = sig_a
    session_state["cables_info_a"] = cab_info_a

    solver = CharmsatSolver(current_rules)
    res_a = solver.solve(sig_a, c_sizes_a)
    session_state["alloc_a"] = res_a

    # Generate Rev B (sizes carried from Rev A, never inferred per signal)
    sig_b, diff_meta = gen.generate_revision_b(sig_a, cable_sizes=c_sizes_a)
    session_state["signals_b"] = sig_b
    c_sizes_b = diff_meta["cable_sizes"]

    res_b = solver.solve(sig_b, c_sizes_b, prev_allocation=res_a.allocations)
    session_state["alloc_b"] = res_b

    return {
        "status": "DEMO_READY",
        "signals_a_count": len(sig_a),
        "rev_a_success": res_a.success,
        "rev_a_violations": len(res_a.violations),
        "rev_a_cabinets": res_a.cabinets_used,
        "rev_a_runtime": res_a.runtime_s,
        "rev_b_success": res_b.success,
        "rev_b_moves_ours": res_b.rev_summary.moves_ours if res_b.rev_summary else 0,
        "rev_b_moves_scratch": res_b.rev_summary.moves_from_scratch if res_b.rev_summary else 0
    }

# Mount static frontend build if present
dist_folder = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if dist_folder.exists():
    app.mount("/", StaticFiles(directory=str(dist_folder), html=True), name="frontend_dist")

