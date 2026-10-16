# CHARMSAT — Empirical Benchmark Report
**Project:** IO SIGNAL SUDOKU | CODE APEX 3.0 Hackathon (VIT Pune)  
**Team:** lost_in_the_shine | **Lead:** Prathmesh Vishwakarma  
**Engine:** OR-Tools CP-SAT + Independent Verification Engine  

---

## 1. Status: being re-measured (integrity pass P0, Oct 2026)

The tables previously in this file mixed measured solver output with
hard-coded columns (greedy Rev B moves were `int(N*0.85)` / `int(N*0.42)`,
the from-scratch figure used a `4*ours+15` floor, one efficiency column was
typed in as `1.00x`). They have been removed. No number below is claimed
until code measures it.

Reproduce (writes `bench/results.csv`, `results.md`, `results.json`,
`meta.json`; the Benchmarks screen reads those files):

```bash
make bench
```

Method (per blueprint §10.6): synthetic generator at N ∈ {1k, 5k, 10k}
(seed 42) plus the organiser sample (local only) and the adversarial set;
baselines B1 grouped-greedy (honest: reports unplaced) and from-scratch
re-solve for revisions; metrics violations (checker), coverage, cabinets,
lower bound, gap, Rev B moves (ours vs scratch, % of unchanged signals),
runtime, determinism hash — all measured in the run, with machine, date
and commit hash.

## 2. Reference prototype results (for orientation, NOT repo claims)

The numbers quoted in the blueprint (`CHARMSAT_v2_Blueprint_and_Playbook.md`
§1.2) were produced by `reference/bench.py` on 15 Oct 2026 (2-vCPU sandbox,
Python 3.13, OR-Tools 9.15, deterministic single-worker mode). They describe
the prototype being ported in P2-1, not the current repo engine. See
`reference/results/*.jsonl` for the raw measured output.

---

## 3. Analysis & Key Insights (to be rewritten from `make bench` output)

1. **Why Naive Greedy (B0) Fails:** fills slots in file order, severing
   multi-pair cables across CIOCs/baseplates and mixing Train A/B.
   (Counts to be re-measured.)
2. **Why Heuristic Grouping (B1) Is Fragile:** A/B-aware but no global
   lookahead; re-packs revisions from scratch. (Counts to be re-measured.)
3. **CHARMSAT:** interval packing with CP-SAT `NoOverlap` + alignment
   constraints; revision via keep-literals weighted by disturbed signals.
   (Counts to be re-measured.)
