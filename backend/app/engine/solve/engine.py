"""Three-stage allocation engine (P2-1) + revision with keep literals (P2-2 core).

solve_allocation: repo Signals -> AllocResult (+ core placements for later
revisions). solve_revision: Rev B with keep literals, a from-scratch
baseline for contrast, and a MoveRecord per moved signal. Forcing-rule
attribution per move is P4-2; until then the field is empty (never guessed).
"""
import time
from typing import Dict, List, Optional, Tuple

from app.models.domain import AllocResult, RevisionSummary, RevisionMoveDetail
from app.models.rules import RuleSetConfig
from app.engine.solve import core
from app.engine.solve.bridge import (
    rules_to_ref, to_core_signals, build_alloc_result,
)

# core cable_id -> (cabinet, cioc, start), 0-based; feeds keep literals.
PrevMap = Dict[str, Tuple[int, int, int]]


def _to_prev(placements: Dict[str, "core.Placement"]) -> PrevMap:
    return {cid: (p.cabinet, p.cioc, p.start) for cid, p in placements.items()}


def _from_prev(prev: PrevMap) -> Dict[str, "core.Placement"]:
    return {cid: core.Placement(cabinet=c, cioc=k, start=s) for cid, (c, k, s) in prev.items()}


def solve_allocation(signals, cable_sizes: Dict[str, int], rules: RuleSetConfig,
                     prev: Optional[PrevMap] = None) -> Tuple[AllocResult, PrevMap, dict]:
    """Returns (AllocResult, prev-map for revisions, raw core result)."""
    ref_rules = rules_to_ref(rules)
    core_sigs = to_core_signals(signals)
    row_lookup = {s.tag: s.row_no for s in signals}
    t0 = time.time()
    res = core.allocate(core_sigs, dict(cable_sizes), ref_rules,
                        prev=_from_prev(prev) if prev else None)
    res["runtime_s"] = round(time.time() - t0, 2)
    out = build_alloc_result(res, rules, row_lookup)
    return out, _to_prev(res.get("placements", {})), res


def _move_kind(a, b) -> str:
    if a[0] != b[0]:
        return "cabinet"
    if a[1] != b[1]:
        return "cioc"
    return "slot"


def solve_revision(signals_b, sizes_b: Dict[str, int], rules: RuleSetConfig,
                   prev: PrevMap, signals_a, rows_a: List[dict],
                   core_a) -> Tuple[AllocResult, PrevMap, dict]:
    """Rev B via keep literals + from-scratch baseline (both measured)."""
    ref_rules = rules_to_ref(rules)
    core_b = to_core_signals(signals_b)
    row_lookup_b = {s.tag: s.row_no for s in signals_b}

    t0 = time.time()
    res_b = core.allocate(core_b, dict(sizes_b), ref_rules, prev=_from_prev(prev))
    res_b["runtime_s"] = round(time.time() - t0, 2)
    if not res_b.get("ok"):
        out = build_alloc_result(res_b, rules, row_lookup_b)
        return out, {}, res_b

    res_s = core.allocate(core_b, dict(sizes_b), ref_rules)  # from scratch
    mv = core.count_moves(rows_a, res_b["rows"], core_a, core_b)
    ms = core.count_moves(rows_a, res_s["rows"], core_a, core_b)

    pos_a = {r["tag"]: (r["cabinet"], r["cioc"], r["baseplate"], r["slot"])
             for r in rows_a if r["tag"]}
    pos_b = {r["tag"]: (r["cabinet"], r["cioc"], r["baseplate"], r["slot"])
             for r in res_b["rows"] if r["tag"]}
    key_a = {s.tag: (s.cable, s.pair) for s in core_a}
    key_b = {s.tag: (s.cable, s.pair) for s in core_b}
    tags_a, tags_b = set(key_a), set(key_b)
    added = tags_b - tags_a
    deleted = tags_a - tags_b
    common = tags_a & tags_b
    changed = {t for t in common if key_a[t] != key_b[t]}
    new_by_tag = {r["tag"]: r for r in res_b["rows"] if r["tag"]}

    details: List[RevisionMoveDetail] = []
    moved_tags = [t for t in common - changed
                  if t in pos_a and t in pos_b and pos_a[t] != pos_b[t]]
    for t in sorted(moved_tags):
        a, b = pos_a[t], pos_b[t]
        kind = _move_kind(a, b)
        r = new_by_tag[t]
        details.append(RevisionMoveDetail(
            tag=t, cable=r["cable"], io_type=r.get("io_type") or "",
            group=r.get("group") or None,
            old_location=f"CAB-{a[0]:02d} / CIOC-{a[1]} / BP-{a[2]} / S-{a[3]}",
            new_location=f"CAB-{b[0]:02d} / CIOC-{b[1]} / BP-{b[2]} / S-{b[3]}",
            forcing_rule="",
            reason=f"{kind} changed; forcing-rule attribution planned (P4-2)",
        ))

    out = build_alloc_result(res_b, rules, row_lookup_b)
    out.rev_summary = RevisionSummary(
        added_count=len(added), deleted_count=len(deleted),
        changed_count=len(changed), moved_count=len(details),
        unchanged_count=len(common - changed) - len(details),
        affected_cabinets=mv.get("cabinets_touched", []),
        moves_ours=len(details), moves_from_scratch=ms.get("moved", 0),
        moves_detail=details,
    )
    return out, _to_prev(res_b.get("placements", {})), res_b
