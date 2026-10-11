# CHARMSAT — 3-Minute Live Hackathon Demo Script
**Event:** CODE APEX 3.0 (VIT Pune) | **Problem Statement:** IO SIGNAL SUDOKU  
**Team:** lost_in_the_shine | **Lead:** Prathmesh Vishwakarma  

---

## Demo Timing & Sequence (Matching Pitch Deck)

### [0:00 – 0:40] Introduction & The Problem
- **Speaker:** "Good morning judges. Control engineers today spend hundreds of hours manually arranging 10,000+ IO signals into cabinets, CIOCs, baseplates, and CHARMs using Excel. When a customer sends Rev B, engineers have to recheck every single rule by eye. One wrong slot means physical rewiring on site. Our solution is **CHARMSAT**: a rule-driven constraint optimization engine powered by OR-Tools CP-SAT and backed by an independent verifier that guarantees zero rule violations."

---

### [0:40 – 1:10] Step 1: Upload & Column Auto-Mapping (Screen 1)
- **Action:** Open `Screen 1: Upload & Mapping`.
- **Action:** Click **"LOAD DEMO FILE"** (1,000 Signals).
- **Showcase:**
  - Point to the **Rapidfuzz Confidence Bar** showing automatic column resolution (e.g. `TAG_NAME` → `Tag`, `CHANNEL_TYPE` → `IO Type`).
  - Toggle **"Fuzz Headers"** to show resilience against messy real-world customer spreadsheets.
  - Click **"Confirm Mapping & Proceed to Solve"**.

---

### [1:10 – 1:35] Step 2: Rule Panel & Natural Language Assistant (Screen 2)
- **Action:** Navigate to `Screen 2: Rule Panel`.
- **Showcase:**
  - Show that rules are **data, not hardcoded logic**.
  - Point to editable parameters resolving problem statement ambiguities:
    - *A/B Segregation level* (CIOC vs Cabinet).
    - *Small Cable Straddling* (6/2-pair boundary crossing toggle).
    - *Spare Margin slider* (10% to 20%).
    - *Naming Patterns* (DeltaV AR1CIOC vs 3-digit numeric).
  - Demonstrate the **Natural Language Rule Assistant**:
    - Type: `"Segregate Train A and Train B signals at CIOC level"`.
    - Click **"Compile to Rule Draft"** → Explain that AI is strictly restricted to wording syntax and *never places signals*.
  - Show the live **YAML Rule Preview**.

---

### [1:35 – 2:05] Step 3: Physical DeltaV Cabinet Grid & KPIs (Screen 3)
- **Action:** Navigate to `Screen 3: Allocation Grid`.
- **Showcase:**
  - **KPI Cards:** Point to `1,000 SIGNALS PLACED (100% COVERAGE)`, `0 VIOLATIONS`, `4 / 4 CABINETS (1.00x Optimal LB)`, `16.9% SPARE`, `RUNTIME 1.37 s`.
  - **Physical Layout:** Explain the 4 CIOCs per cabinet, 8 baseplates per CIOC, 12 CHARMs per baseplate (384 slots/cabinet).
  - Hover over a slot: show the interactive tooltip displaying `Tag`, `Cable`, `Pair`, `CHARM Model (AI 4-20mA HART)`, and `Terminal Block`.
  - Point out the **TRAIN A (Cyan)** and **TRAIN B (Amber)** segregation badges on CIOC headers.

---

### [2:05 – 2:30] Step 4: The Credibility Demo — Plant a Violation (Screen 4)
- **Action:** Navigate to `Screen 4: Checker Report`.
- **Showcase:**
  - Point to the glowing green badge: **"0 VIOLATIONS — CLEAN AUDIT // VERIFIED"**.
  - Explain: *"Judges might ask: does your checker just share your solver's bugs? No. It is an independent module with zero shared code."*
  - **The Hook:** Click **"Plant A/B Leak"**!
  - The screen flashes red with **36 VIOLATIONS CAUGHT**. Point to the exact offending row highlighted in red where an A signal was leaked into a B CIOC.
  - Click **"Reset to Clean"** to return to 0 violations.

---

### [2:30 – 2:50] Step 5: Infeasibility & TQs (Screen 5)
- **Action:** Navigate to `Screen 5: Technical Queries (TQs)`.
- **Action:** Click **"LOAD ADVERSARIAL CONFLICT FILE"**.
- **Showcase:**
  - Explain: *"When real-world data is contradictory, CHARMSAT never crashes or silently drops signals. It isolates the Minimal Unsatisfiable Subset (MUS)."*
  - Expand `TQ-RUL-UNSAT-01`: show the plain-English explanation: *"Cable CBL-105 carries both Train A and Train B signals: Rule 1 (A/B Segregation) and Rule 2 (Cable Contiguity) conflict."*

---

### [2:50 – 3:15] Step 6: Minimum-Move Revision B (Screen 6)
- **Action:** Click **"DEMO MODE"** to reset, then navigate to `Screen 6: Revision Diff`.
- **Showcase:**
  - Point to the huge numbers:
    - **OURS (Min-Move Engine): 26 Moves**
    - **From-Scratch Re-solve: 221 Moves**
  - Highlight: *"Because our solver treats Rev A as soft hints with a heavy move penalty, 97.4% of field terminations remain untouched. This saves hundreds of thousands of dollars in site rewiring costs."*
  - Scroll down to the cabinet grid: point to the few relocated slots pulsing in **neon amber**.

---

### [3:15 – 3:35] Step 7: Empirical Benchmarks (Screen 7)
- **Action:** Navigate to `Screen 7: Benchmarks`.
- **Showcase:**
  - Live measurements against rivals:
    - **B0 Greedy (File Order):** 865 violations (fails completely).
    - **B1 Greedy (Grouped + A/B):** 6 violations, 420 revision moves (high churn).
    - **CHARMSAT (CP-SAT):** **0 violations**, **1.00x lower bound efficiency**, **1.12 s runtime**.
  - Show the runtime-vs-N line chart proving scale well under 60 seconds at 10,000 signals.

---

### [3:35 – 3:50] Step 8: Production Export (Screen 8)
- **Action:** Navigate to `Screen 8: Export`.
- **Showcase:**
  - Click **"DOWNLOAD FILLED EXCEL (.XLSX)"**.
  - Show that the exported workbook contains all 5 styled sheets: Project Summary KPIs, IO Assignment Matrix, Independent Checker Audit, TQ Log, and Revision B Diff.

---

### [3:50 – 4:00] Conclusion
- *"In summary: CHARMSAT gives EPCs and plant owners guaranteed zero-violation allocations, plain-English TQs, and minimum-move revisions that prevent physical rewiring. Thank you!"*
