import hashlib
import json
import pytest
from hypothesis import given, settings, strategies as st

from app.models.rules import RuleSetConfig
from app.models.domain import Signal
from app.engine.generator import SyntheticGenerator
from app.engine.solver import CharmsatSolver
from app.engine.checker import IndependentChecker
from app.engine.validator import DataValidator
from app.engine.mapper import ColumnAutoMapper

def test_generator_structure():
    gen = SyntheticGenerator(seed=123)
    signals, cables_info = gen.generate_dataset(n_signals=200)
    assert len(signals) == 200
    assert len(cables_info) > 0
    # Every signal belongs to a cable
    cable_ids = {c["cable_id"] for c in cables_info}
    for s in signals:
        assert s.cable in cable_ids
        assert s.pair >= 1

def test_independent_checker_zero_violations_on_valid_allocation():
    gen = SyntheticGenerator(seed=42)
    signals, cables_info = gen.generate_dataset(n_signals=300)
    cable_sizes = {c["cable_id"]: c["size"] for c in cables_info}

    rules = RuleSetConfig()
    solver = CharmsatSolver(rules)
    result = solver.solve(signals, cable_sizes)

    assert result.success is True
    assert len(result.violations) == 0

    # Verify directly with independent checker
    checker = IndependentChecker(rules)
    audit_violations = checker.verify(result.allocations, signals)
    assert len(audit_violations) == 0

def test_hand_planted_violation_caught():
    gen = SyntheticGenerator(seed=99)
    signals, cables_info = gen.generate_dataset(n_signals=250)
    cable_sizes = {c["cable_id"]: c["size"] for c in cables_info}

    rules = RuleSetConfig()
    solver = CharmsatSolver(rules)
    result = solver.solve(signals, cable_sizes)
    assert result.success is True

    checker = IndependentChecker(rules)
    
    # 1. Plant A/B leak
    planted_ab = checker.plant_violation(result.allocations, "ab_leak")
    viols_ab = checker.verify(planted_ab)
    assert len(viols_ab) > 0
    assert any(v.rule_id == rules.ab_segregation.id for v in viols_ab)

    # 2. Plant Split Cable
    planted_split = checker.plant_violation(result.allocations, "split_cable")
    viols_split = checker.verify(planted_split)
    assert len(viols_split) > 0
    assert any(v.rule_id == rules.cable_contiguity.id for v in viols_split)

def test_determinism_same_seed_gives_identical_output():
    """Same seed + same rules => identical allocation hash in TWO SEPARATE
    processes (P1-5). An in-process comparison cannot catch multi-worker or
    wall-clock non-determinism."""
    import subprocess
    import sys
    prog = (
        "import sys, json, hashlib; sys.path.insert(0, 'backend');"
        "from app.models.rules import RuleSetConfig;"
        "from app.engine.generator import SyntheticGenerator;"
        "from app.engine.solver import CharmsatSolver;"
        "gen = SyntheticGenerator(seed=555);"
        "sig, c_info = gen.generate_dataset(n_signals=300);"
        "c_sizes = {c['cable_id']: c['size'] for c in c_info};"
        "res = CharmsatSolver(RuleSetConfig()).solve(sig, c_sizes);"
        "print(hashlib.sha256(json.dumps([a.model_dump() for a in res.allocations], sort_keys=True).encode()).hexdigest())"
    )
    hashes = []
    for _ in range(2):
        out = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, check=True)
        hashes.append(out.stdout.strip())

    assert hashes[0] == hashes[1], "Allocations must be strictly deterministic given the same seed and input"

def test_data_validator_tq_generation():
    validator = DataValidator(spare_pct=10.0)
    bad_signals = [
        Signal(tag="TAG-1", io_type="", cable="CBL-1", pair=1), # blank type
        Signal(tag="TAG-2", io_type="AI", cable="CBL-1", pair=1),
        Signal(tag="TAG-2", io_type="AI", cable="CBL-1", pair=2), # duplicate tag
        Signal(tag="TAG-3", io_type="DI", cable="CBL-2", pair=99), # pair overflow
    ]
    cable_sizes = {"CBL-1": 12, "CBL-2": 6}
    valid, tqs, ledger = validator.validate(bad_signals, cable_sizes)

    assert len(tqs) >= 3
    tq_ids = {t.id for t in tqs}
    assert "TQ-DAT-01" in tq_ids  # blank type
    assert "TQ-DUP-TAG-2" in tq_ids  # duplicate tag
    assert "TQ-PAIR-CBL-2" in tq_ids  # pair overflow
    # Ledger covers every input row
    assert set(ledger) == {"TAG-1", "TAG-2", "TAG-3"}
    assert ledger["TAG-2"].startswith("held:")

def test_fuzzy_column_mapper():
    mapper = ColumnAutoMapper()
    fuzzed_headers = ["TAG_NAME", "CHANNEL_TYPE", "CABLE_TAG", "Pair_No", "Unit_Area", "Safety_Seg", "Junk_Col"]
    res = mapper.map_columns(fuzzed_headers)

    mapped_dict = {m.detected_column: m.mapped_canonical for m in res.matches}
    assert mapped_dict.get("TAG_NAME") == "Tag"
    assert mapped_dict.get("CHANNEL_TYPE") == "IO Type"
    assert mapped_dict.get("CABLE_TAG") == "Cable"
    assert mapped_dict.get("Pair_No") == "Pair"
    assert mapped_dict.get("Unit_Area") == "Group"
    assert mapped_dict.get("Safety_Seg") == "Segregation"
    assert "Junk_Col" in res.unmapped_columns

# Hypothesis property test
@settings(max_examples=3, deadline=20000)
@given(st.integers(min_value=100, max_value=400), st.integers(min_value=1, max_value=1000))
def test_hypothesis_zero_violations_property(n_signals, seed):
    gen = SyntheticGenerator(seed=seed)
    signals, cables_info = gen.generate_dataset(n_signals=n_signals)
    cable_sizes = {c["cable_id"]: c["size"] for c in cables_info}

    rules = RuleSetConfig()
    solver = CharmsatSolver(rules)
    result = solver.solve(signals, cable_sizes)

    assert result.success is True
    checker = IndependentChecker(rules)
    violations = checker.verify(result.allocations, signals)
    assert len(violations) == 0, f"Hypothesis property failed: found {len(violations)} violations on seed {seed}"
