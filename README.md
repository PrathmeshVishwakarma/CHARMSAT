# CHARMSAT — DeltaV IO Signal Sudoku Allocation Engine

**CODE APEX 3.0 Hackathon (VIT Pune)**  
**Problem Statement:** IO SIGNAL SUDOKU  
**Team:** `lost_in_the_shine` | **Team Leader:** Prathmesh Vishwakarma  
**Presentation Deck:** [Google Slides Deck](https://docs.google.com/presentation/d/1E1McJmBBFgO8wkOKil0RFTOfD26JdjVYkOXzegLtJS0/edit?usp=sharing)  

---

## 1. Overview & Architecture

**CHARMSAT** is an offline, rule-driven hardware allocation and verification engine for Emerson DeltaV Electronic Marshalling. It automatically maps field signals into **Cabinet → CIOC → Baseplate → CHARM slot** and re-checks the result with an independent verifier.

> **Integrity status (P0, Oct 2026):** all previously hard-coded demo numbers
> (benchmark table, revision 26/221, "1.00x optimal", "bit-for-bit
> deterministic") have been removed from code and UI. Screens show measured
> values or honest empty states; `make integrity` guards against regression.
> Benchmarks are being re-measured — see `make bench`. Determinism across
> processes is NOT yet guaranteed (fix in progress, P1-5).

### Core Pillars
1. **Rule-Compiled Constraint Optimization:** Formulates signal allocation as a 1-D interval packing problem over atomic multi-pair cable blocks using **Google OR-Tools CP-SAT**.
2. **Independent Verification Engine:** A separate verification module that re-derives the rules from the allocation output. Full package isolation (`backend/checker/` importing nothing from the app) is planned (P2-4); today it shares data models.
3. **Minimum-Move Revisions (Rev A → Rev B):** Uses previous allocations as CP-SAT soft hints with move penalties. Measured move counts are currently high on stock Rev B data — the revision engine is being rebuilt (P2-2).
4. **Technical Queries (TQs):** When customer data or rule constraints conflict, CHARMSAT returns TQs naming the conflict. Minimal-unsatisfiable-subset (MUS) explanations are planned (P4-1); current TQs are rule-conflict templates.
5. **Wording-Only AI Rule Assistant:** Parses plain-English rule drafts into typed constraint configurations. AI *never* places signals. Drafted rules are not yet enforced by the solver (planned, P3).

---

## 2. Quick Start & Execution

CHARMSAT runs 100% offline on a single laptop with a unified single-command launcher.

### Prerequisites
- Python 3.11+ (CI/dev env here: 3.10 — upgrade planned)
- Node.js 18+ for the React UI

> **Status (Oct 2026, integrity pass P0):** the API + solver run from a fresh
> clone. The UI bundle is NOT pre-built — `frontend/dist/` does not exist in
> the repo. Run `make install` (builds the UI) before `make run`.
> (Planned: commit `dist/` on the demo branch for offline finale use.)

### Single-Command Start
```bash
# Option A: Windows Batch File (Double-click or run from terminal)
run_demo.bat

# Option B: Make
make run

# Option C: Direct Python
python run_server.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser. The unified server serves both the FastAPI REST endpoints and the cyber control-room console.

---

## 3. Makefile Targets

```bash
make run    # Launches unified full-stack application at http://127.0.0.1:8000
make bench  # Executes multi-scale empirical benchmark suite (run_bench.py)
make test   # Runs pytest test suite, including Hypothesis property tests
make integrity  # Fails if any fabricated metric literal is (re-)introduced
```

---

## 4. Hardware Capacities & Physical Layout

- **1 Baseplate** = 12 CHARM slots
- **1 CIOC (CHARM I/O Card)** = 8 Baseplates = 96 CHARM slots
- **1 Cabinet** = 4 CIOCs = 32 Baseplates = 384 CHARM slots
- **Slot Indexing:**
  - $BP = \lfloor \text{slot\_in\_cioc} / 12 \rfloor$
  - $\text{slot} = \text{slot\_in\_cioc} \bmod 12$
  - $\text{cioc} = \lfloor \text{slot\_in\_cab} / 96 \rfloor$

---

## 5. Engineering Assumptions & Ambiguities Resolved

The competition specification leaves several real-world edge cases ambiguous. CHARMSAT exposes all of them as configurable parameters in the **Rule Panel**:

1. **Cable Boundary Straddling:**
   - *Ambiguity:* Whether 6-pair or 2-pair cables may straddle two physical baseplates.
   - *Resolution:* 24-pair and 12-pair cables are strictly aligned to baseplate boundaries (`st_c % 12 == 0`). For 6-pair and 2-pair cables, the parameter `allow_boundary_crossing_small` is exposed in the Rule Panel (default: `False` / forbidden).
2. **Group "In Sequence":**
   - *Ambiguity:* The PS mentions tags landing "in sequence" within a group.
   - *Resolution:* Enforcing hard monotonic sequencing causes valid real-world files to become mathematically infeasible. CHARMSAT implements group sequence as a soft lexicographic objective penalty (`soft_sequence_weight = 5`), ensuring groups co-locate in the same cabinet while keeping placement feasible.
3. **CIOC Asset Naming Convention:**
   - *Ambiguity:* The spec shows `<CIOC no>-CBP-<n>` (e.g. `001-CBP-1`) alongside `AR1CIOC100001`.
   - *Resolution:* Exposed as `cioc_no_format` parameter in the Rule Panel:
     - `deltav_ar1`: Emerson convention (`AR1CIOC0101`)
     - `numeric_3digit`: 3-digit numeric sequence (`001-CBP-1`)
     - `hierarchical`: Cabinet-prefixed (`CAB-01-CIOC-01`)
4. **Isolated DO Subtypes:**
   - *Resolution:* DO signals with subtype `SOV`, `horn`, `beacon`, or `ISOLATED` automatically map to `DO 24V DC Isolated` CHARMs with `Relay TB` terminal blocks.

---

## 6. Verification & Quality Checks

Run the automated test suite:
```bash
make test
# or: python -m pytest backend/app/tests/test_unit.py -v
```

The test suite validates:
- **Hypothesis Property Test:** For arbitrary valid synthetic inputs, the independent checker reports **0 violations** on CHARMSAT output.
- **Hand-Planted Violation Test:** Verifies that deliberately tampered copies (A/B leak, broken contiguity) are immediately detected by the independent checker.
- **Determinism (IN PROGRESS, P1-5):** `test_determinism_same_seed_gives_identical_output` currently FAILS intermittently (also on pristine code) — CP-SAT runs multi-worker with wall-clock limits. Fix: single worker + deterministic time, as in `reference/charmsat_core.py`.
- **Data Validator TQs:** Confirms blank IO types, duplicate tags, and pair overflows raise technical queries.

---

## 7. Deliverables & Screenshots

All 8 workflow screens have been captured in **1920x1080** and are stored in `/screenshots`.
> **Stale:** these were captured from runs containing hard-coded numbers
> (e.g. revision "26 vs 221 moves"). They will be retaken from real runs
> after the engine rebuild (P2).
- `01_mapping.png`: Drag-and-drop file ingestion with rapidfuzz confidence matching.
- `02_rule_panel.png`: Parameterized rule cards, live YAML preview, and Natural Language Rule Assistant.
- `03_allocation.png`: DeltaV physical cabinet matrix (4 CIOCs × 8 BPs × 12 slots) with KPI cards.
- `04_checker.png`: Independent checker audit with **0 VIOLATIONS** badge and "Plant a Violation" credibility demo.
- `05_tqs.png`: Technical Queries manager with expandable Minimal Conflicting Subsets (MUS).
- `06_revision.png`: Rev A vs Rev B diff summary with side-by-side min-move comparison (STALE: shows hard-coded 26 vs 221 — will retake).
- `07_benchmark.png`: Multi-algorithm comparison (B0 Greedy vs B1 Grouped vs CHARMSAT) with runtime curves (STALE — will retake from `make bench`).
- `08_export.png`: Filled Excel workbook download with 5 pre-formatted worksheets.

---

## 8. Known Limitations

1. **Brand-New Rule Semantics:** Adding completely novel physical constraints outside the standard relation taxonomy (`same`, `different`, `at_most_k`) requires defining a new `Rule` class. Parameter adjustments, group rules, and spare modifications require zero code changes.
2. **DCS Scope:** Tailored specifically to the Emerson DeltaV Electronic Marshalling architecture. Other DCS topologies (e.g. traditional marshalled racks) are excluded from Phase 1.
