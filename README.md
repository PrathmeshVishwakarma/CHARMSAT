# CHARMSAT — DeltaV IO Signal Sudoku Allocation Engine

**CODE APEX 3.0 Hackathon (VIT Pune)**
**Problem Statement:** IO SIGNAL SUDOKU
**Team:** `lost_in_the_shine` | **Team Leader:** Prathmesh Vishwakarma

---

## 1. What this is

**CHARMSAT** turns a customer IO list (Excel) into a complete Emerson DeltaV
Electronic Marshalling allocation — cabinet → CIOC → baseplate → CHARM slot,
CHARM + terminal block, generated names — with zero rule violations,
verified by an independent checker that reads the exported workbook. When
data or rules make placement impossible it raises a Technical Query (TQ)
naming the cause and fix. Rev B re-allocates keeping unchanged signals put.

## 2. Run it from a fresh clone

```bash
git clone <repo> && cd CHARMSAT
make install   # backend deps + frontend build
make run       # API + UI at http://127.0.0.1:8000
```

Works fully offline (no LLM, no network). Python 3.10+ and Node.js 18+
(passed here on Python 3.10, Node 23). Organiser sample/template, if you
have them, go in `data/organiser/` (gitignored) — never committed.

```bash
make test       # full pytest suite
make integrity  # fails if a fabricated metric literal is (re-)introduced
make bench      # measures everything, writes bench/results.*
make demo-check # upload -> allocate -> export -> check -> revise (exit 0)
```

## 3. What works for real, what is stubbed, what is planned

**Works (measured, tested):**

- Real xlsx/csv upload: header-row detection, synonym + value-sniffed
  column mapping with evidence, manual override applied to data, multi-sheet.
- Validator: duplicate tags/pairs, pair overflow, missing cable, unknown
  types/subtypes, multi-group and A+B-mixed cables, giant cables — each a TQ
  with all tags + Excel rows; coverage ledger (placed + held = 100%).
- Three-stage engine (ported from `reference/`): units→cabinets (CP-SAT +
  proven lower bound), cables→CIOCs (exact, per cabinet), slots (exact FFD;
  CP-SAT fallback). Deterministic across processes (single worker +
  deterministic time + fixed seed; identical hashes verified).
- Independent checker (`backend/checker/`, imports nothing from the app)
  reads the written workbook + IO rows; every allocation is verified on
  export bytes; "plant a violation" demo (7 plants, all caught).
- Template writer: results into a COPY of the template, values only,
  formula refusal, XML fallback preserving drawings, fidelity-tested;
  export carries TQ log + audit (output hash).
- Revisions: Rev B upload with tag-level diff, keep-literal re-solve +
  measured from-scratch baseline, per-move records (forcing-rule text
  pending, field left empty, never guessed).
- `make bench` slide table + Benchmarks screen reading it; honest B0/B1
  baselines (violations + unplaced reported, moves measured).
- PDS-correct hardware table (data) and token naming patterns
  (`AR1CIOC100001`, `001-CBP-1` reproduced).

**Stubbed / simplified:**

- Rule set is still the Python config object (all parameters flow to solver
  + checker); the YAML rule language with schema validation is planned
  (P3) — custom rule *kinds* need code today, new rules of existing kinds
  are config-only.
- Mapping profiles are not yet saved per customer; organiser-template map
  ships only when their template is available (synthetic stand-in used).
- Move forcing-rule attribution is empty text (P4-1/P4-2: unit explainer +
  MUS wording, impact report details).
- Screenshots in `/screenshots` predate the rebuild — retake planned.

**Planned next (blueprint §11.4 SHOULD/WOW):** P3 rule language + live-added
rule demo, P4 TQ explanations + move provenance, P6 adversarial/property CI,
W1 what-if cards, W2 "why is this signal here", W3 offline AI rule drafts.

## 4. Demo script (3 minutes, all live)

Files (generated, fixed seeds): `demo/unseen_messy.xlsx` (1,000 signals,
messy headers, 2 defects), `demo/rev_b.xlsx`, `demo/planted_ab_leak.xlsx`.
Fallbacks in `DEMO_SCRIPT.md` / blueprint §13.3. Pre-flight:
`make demo-check` (13/13 green).

| Time | Action | Point |
|---|---|---|
| 0:00 | Upload `demo/unseen_messy.xlsx` → mapping with evidence → Allocate | Unseen data; 4 cabs / LB 4 / OPTIMAL; 100%; 0 viols; 2 TQs |
| 0:50 | Checker → plant A/B leak → red → reset | Independent checker is real |
| 1:15 | TQs | Each names rules, rows, fix options |
| 1:40 | Upload `demo/rev_b.xlsx` → Revise | Ours vs scratch moves, both live |
| 2:15 | Export | Filled template + output hash; re-run identical |

## 5. Real numbers (`make bench`, 2026-10-16, 8 CPUs, commit e0ab872)

Full table: `BENCHMARK.md` (source: `bench/results.*`).

- 1,000 signals: **4 cabinets / LB 4 (optimal)**, 0 violations, Rev B
  **24 moves (2.4%) vs 971 scratch**, 0.06 s.
- 5,000: 20 / 19 (gap 1), 0 violations, 473 (9.7%) vs 4641, 9.2 s.
- 10,000: 39 / 38 (gap 1), 0 violations, 1141 (11.6%) vs 8972, 8.4 s.
- Greedy baselines use fewer cabinets only by breaking rules (hundreds to
  thousands of violations) — illegal packing, captioned as such.

## 6. Open questions for the organisers (code depends on these)

1. "≈10% spare": whole empty baseplates per cabinet, rounded up or down?
   (Default: `ceil(10% × 32) = 4`; configurable.)
2. "Keep groups together": same cabinet, CIOC, or consecutive slots?
   (Default: cabinet.)
3. May 2/6/12-pair cables straddle baseplates; may 24-pair start anywhere?
   (Defaults: no; any boundary.)
4. Exact naming patterns; what is "CIOC no"? (Defaults reproduce both
   PS examples; token patterns configurable.)
5. Data breaking a rule: is a TQ the expected output, or must we split?
6. Revision: is a CHARM swap at the same slot a "move"? Cabinets vs moves
   priority? (Defaults: hardware change ≠ move; 1 cabinet = 200 moves.)
7. Hidden IO list headers / DO subtype words same as sample?
8. Does the template contain formulas/charts/images that must survive?
   (Values-only writer + XML fallback ready.)

## 7. Declarations

Python, OR-Tools CP-SAT, pandas, openpyxl, rapidfuzz, FastAPI, pydantic,
PyYAML, jsonschema, pytest, Hypothesis, React/Vite/Tailwind. Reference
prototype + this build assisted by Claude (Anthropic) — declared AI tool;
no LLM in solver/checker, app works offline. Sample data/template (if
placed in `data/organiser/`) are hackathon-only, gitignored, never sent
anywhere. Rule interpretations A1–A16 default per blueprint §3.

## 8. Hardware & layout reference

- 1 baseplate = 12 CHARM slots; 1 CIOC = 8 baseplates = 96 slots;
  1 cabinet = 4 CIOCs = 32 baseplates = 384 slots.
- Spare rule: ≥ `ceil(10% × 32)` = 4 empty baseplates per used cabinet.
