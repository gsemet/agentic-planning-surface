# Price correction: Sonnet 5.5 cache reads at $0.10/MTok (was $0.20)

- **Date:** 2026-10-27. Same transcripts, same cut-offs, same scripts. Only prices changed.
- **Official table** (`research2/docs/api-pricing.md` lines 15–45, footnote 2): Sonnet 5.5 is
  2 / 2.50 / 4 / **0.10** / 10 $/MTok (input, 5-min write, 1-h write, cache read, output). Cache
  reads on Opus 5.5 and Sonnet 5.5 cost 0.05× base input. Opus 4 / 5 / 8 / 0.20 / 20, Haiku 5.5
  0.10 / 0.125 / 0.20 / 0.01 / 0.50 (prompt ≤100k) and 0.50 / 0.625 / 1 / 0.05 / 2.50 (prompt
  >100k, whole request), Fable 5.1 10 / 12.5 / 20 / 0.25 / 50.
- **Consequence:** Sonnet 5.5 is now exactly **0.5× Opus 5.5 on every billing category**. Every
  earlier statement that "Opus and Sonnet reads cost the same" is wrong.
- **Transcripts** use only `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-haiku-5-5` and
  `claude-fable-5-1` (checked across all `~/.claude/projects/**/*.jsonl` modified since 10-16).

## How this was recomputed

- Scripts copied to `research3/scripts/{D1,A1,A2}/`; originals untouched. The patch is
  `research3/patch.py`:
  - `common.py` (each copy): Sonnet cache read 0.20 → 0.10; per-turn `cost` recomputed at load
    from the stored token counts (the jsonl files carry the old `cost`); helper `PT(t)` applies
    the Haiku >100k tier (prompt = input + cache read + cache writes); data paths point read-only
    at `research/data/` and `research2/{scripts/data,data/A2}/`.
  - every `PRICE[t["fam"]]` → `PT(t)`; `a1_sim.py` prices Haiku on the simulated context S.
  - hard-coded Sonnet constants re-derived: `a2_options.py` driver event (0.2 → 0.1 read),
    `fresh_pre` Sonnet $0.18–0.22 → $0.15–0.17 (corrected `a2_fresh.py`), `a2_combine.py`
    `DRV` 0.148 → 0.142, `pre` 0.22 → 0.17, all-in $/CR 6.93/4.86/3.72 → 5.50/3.54/3.09.
  - `A1/x_haiku_low.py` (new): Haiku on the conservative path, which A1 had only estimated.
- **Baseline check:** a second copy (`research3/scripts_base/`, old prices) reproduces every
  published output byte for byte (`out_base/`), except design-1 `out_c.txt` (§4.2 turn classes),
  which was produced before `common.py` was last edited (22:50 vs 22:52). Price-only deltas for
  that table are taken against the rerun.
- **Outputs:** `research3/out/{D1,A1,A2}/` (corrected), `research3/out_base/` (old prices).
- **Haiku and Fable audit:**
  - Design-1 `extract.py`/`common.py` priced Haiku flat. 11 Haiku turns exceed 100k: Haiku
    $0.096 → **$0.196** (agent "Page-side DOM performance", $0.055 → $0.154). Negligible in totals.
  - A1 `a1_sim.py` priced **Haiku flat in every Haiku scenario: wrong** (see A1 §7 below).
  - A2 `a2_models.py` applied ×5 when input + read + writes > 100k: **correct** (unchanged numbers).
  - Fable 5.1 priced correctly (10 / 12.5 / 20 / 0.25 / 50). Leftover scripts not used by these
    reports (`agent_cost.py`, `main_session.py`) price Fable as Opus; `stats.py` has pre-5.x prices.

## 1. Window totals (design-1 data, 947 agents, 32,846 turns, 7.6 days)

| Item | Before | After |
| --- | --- | --- |
| **Total** | **$1,705.5** (≈ $1,573/wk) | **$1,438.4** (≈ $1,325/wk), −15.7 % |
| Sonnet | $992.4 | **$725.2** |
| Opus | $705.3 | $705.3 |
| Fable | $7.8 | $7.8 |
| Haiku | $0.1 | $0.2 (>100k tier) |
| Cache reads | $827.8 (48.5 %) | **$560.7 (39.0 %)** |
| 5-min writes | $488.4 (28.6 %) | $488.4 (34.0 %) |
| Output | $276.9 (16.2 %) | $276.9 (19.3 %) |
| 1-h writes | $112.2 (6.6 %) | $112.2 (7.8 %) |
| Uncached input | $0.2 | $0.2 |

| Role | Before | After | Cache read before → after |
| --- | --- | --- | --- |
| Coder / writer | $777.6 (45.6 %) | $638.7 (44.4 %) | $411.1 → $272.2 |
| Main session (Opus) | $278.4 (16.3 %) | $278.4 (19.4 %) | $117.8 → $117.7 |
| Reviewer | $222.7 | $177.2 | $107.1 → $61.6 |
| Analyst | $191.3 | $144.9 | $107.0 → $60.5 |
| Orchestrator | $115.2 | $96.2 | $39.7 → $20.8 |
| Driver (per CR) | $83.8 | $76.2 | $23.5 → $15.9 |
| Stack driver | $23.3 | $15.0 | $16.6 → $8.3 |
| Task driver | $7.8 | $6.7 | $2.1 → $1.1 |
| Integrator | $1.2 | $0.9 | $0.6 → $0.3 |
| Other | $4.2 | $4.2 | – |

| Workstream | Before | After |
| --- | --- | --- |
| Requirements base (CRs 059/060) | $497.4 | $371.9 |
| CR pipeline before run 1 | $384.7 | $331.4 |
| Main session (white paper) | $235.6 | $235.6 |
| CR 056 refactor | $153.1 | $153.1 |
| CR factory run 1 | $110.8 | $86.5 |
| Deep-UX fix plan | $99.2 | $71.6 |
| CR factory run 4/5 | $92.0 | $74.7 |
| Other projects (main) | $42.8 | $42.8 |
| CR factory run 2 | $33.4 | $24.2 |
| One-off tasks | $26.2 | $19.6 |
| Audit research | $17.8 | $16.6 |
| CR factory run 3 | $12.5 | $10.6 |
| Factory scope (runs 1–5 + earlier batches) | $633.5 (37 %), ≈42 % with main orchestration | $527.4 (37 %), ≈43 % |

A1's slightly longer extract (958 agents): $1,719.2 ($1,581/wk) → **$1,449.3 ($1,333/wk)**.
A2's worker scope: $1,191.6 (70 %) → **$960.8 (67 %)**.

## 2. Design-1 (`research/01-costs.md`)

### 2.1 Runs and per CR (§3)

| Run | Subtree | Orchestration own (overhead) | $/CR subtree | Coder+reviewer $/CR | All-in $/CR today | Sketch $/CR | Cut |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | $110.79 → **$86.47** | $35.25 (32 %) → $27.28 (32 %); stack driver $16.90 → $10.88 | $6.52 → $5.09 | $4.44 → $3.48 | $6.93 → **$5.50** | $4.99 → $3.95 | 28 % → 28 % |
| 2 | $33.44 → $24.16 | $7.57 (23 %) → $5.89 (24 %) | $4.78 → $3.45 | $3.70 → $2.61 | $4.86 → **$3.54** | $4.01 → $2.88 | 18 % → 19 % |
| 3 | $10.10 → $8.22 | $5.11 (51 %) → $4.48 (55 %) | $3.37 → $2.74 | $1.66 → $1.24 | $3.72 → **$3.09** | $2.27 → $1.82 | 39 % → 41 % |
| 4/5 | $94.44 → $77.12 | $15.62 (17 %) → $13.97 (18 %) | $13.49 → $11.02 | $11.26 → $9.02 | $13.65 → $11.18 | $11.48 → $9.20 | 16 % → 18 % |

`i_percr.py` keeps its hard-coded $0.01 per runner and $0.55 per extra round; the corrected
fresh-coder cost ($0.40–0.68 mean) has the same midpoint, so they were left as is.

Per CR (own subtree), before → after:

- Run 1: 107 $2.13→1.70; 108 $0.97→0.74; 109 $5.00→3.91; 110 $5.85→4.35; 111 $2.15→1.56;
  112 $4.78→3.55; 113 $3.60→2.80; 114 $4.35→2.98; **115 $15.76→13.00**; 116 $2.93→2.31;
  117 $2.53→1.73; 118 $2.18→1.55; 119 $4.64→3.10; 120 $2.34→1.70; 121 $2.02→1.42;
  **123 $21.01→19.04**; 124 $1.65→1.20.
- Run 2: 125 $1.66→1.30; 126 $2.41→1.74; 127 $1.18→1.00; 128 $2.30→1.70; 129 $3.87→2.67;
  130 $4.93→4.26; **131 $12.39→8.11**.
- Run 3: 132 $1.36→1.07; 133 $1.92→1.56; 134 $2.60→1.87.
- Run 4/5: **135 $63.88→54.84** (coders $41.4→34.5, reviewers $13.5→12.75, task drivers
  $7.77→6.70, integrators $1.21→0.89); 137 $1.22→0.99; 138 $3.78→2.55; 139 $3.97→2.84;
  140 $2.26→1.63; 141 $5.07→3.37; 143 $9.76→6.39.
- Earlier batches: $384.7 → $331.4, orchestration own $94.7 → $82.2 (25 % → 25 %).
  P1+P2 orchestrator subtree $123.43 → $96.43 (own $40.03 → $33.55).

### 2.2 Lever 1 base (§4.1–4.2)

| Scope | Own cost | Rebuilds | Rebuild excess |
| --- | --- | --- | --- |
| Runs 1–5 | $63.54 → $51.63 | 95 | $18.0 → $18.6 |
| Earlier CR batches | $94.71 → $82.17 | 118 | $39.3 → $40.6 |
| Other workstreams | $73.00 → $61.21 | 58 | $34.1 → $34.9 |
| **Total** | **$231.3 (≈ $213/wk) → $195.0 (≈ $180/wk)** | 271 | **$91.4 (40 %) → $94.1 (48 %)** |

Rebuild excess (write minus a warm read) **rises**, because the warm read it is compared with is
cheaper. Top agents: P1+P2 orchestrator $40.03 → $33.55; Orchestrator L $25.11 → $18.55;
Driver CR 056 (Opus) $20.39 unchanged; run-1 stack driver $16.90 → $10.88 (run-1 orchestrator
$6.97 → $6.44).

Turn classes (§4.2): mechanical share 86.2 % published / 87.3 % on the rerun at old prices →
**86.8 %** corrected; judgment $31.9 (13.8 %) → **$25.7 (13.2 %)**. Steering $10.45 → $10.23
direct. Low end of the lever stays 75 %.

### 2.3 Levers 2–4 and TTL (§5)

- **Lever 2** removable rebuild excess: coders long suites $41.75 → $42.40, CI $9.94 → $10.26,
  background $5.49 → $5.69; reviewers $3.0 → $3.1; analysts $1.7 → $1.7. **Base $61.9 → $63.2;
  factory scope $31.9 → $32.4.** Weekly at 70–100 %: **$40–57 → $41–58** (still CONFIRMED).
  Per-role excess: orchestrator $53.1 → $55.2, driver $33.9 → $34.3, coder $87.1 → $89.3,
  main $62.3 unchanged.
- **Lever 3:** coder shell reads $163.3 → **$124.9** (factory $90.6 → $69.5); command output
  (fast gates, long suites, gh) $3.6 → $2.8; output cap at 1k tokens: coders $16.9 → $12.9,
  reviewers $10.6 → $8.4, others $5.6 → $3.9; targeted-read upper bound $46 → $34 (25–50 %:
  $10–21/wk → **$8–16/wk**); fresh-coder cost before first edit, median (mean): round 1
  $0.44 ($0.68) → $0.35 ($0.59), round 2 $0.25 ($0.42) → $0.22 ($0.40), round 3+ $0.63
  ($0.69) → $0.63 ($0.68); hand-over note $6–15 → ≈ $6–15/wk (−3 %). Resumed agents after a
  hand-back $108.5 → $87.2. **Lever 3 total $15–40 → $14–32/wk.**
- **TTL (§5.3):** 5-min writes unchanged ($488.4, rebuilds $221.1). One-hour TTL today:
  rebuilds <1 h saved $195.5 → $201.1; **net −$28.2 → −$33.7 in the window** (factory sub-agents
  −$23.3 → −$26.1). After levers 1 and 2: +$94.4 → **+$92.6 window (+$87 → +$85/wk)**. Verdict
  unchanged: rejection CONFIRMED, stop-gap holds.
- **Lever 4:** unchanged (main sessions are Opus): $198.10, orchestration $84.68 (43 %),
  autocompact −23 % / −21 %, **$65–105/wk**.

### 2.4 Added costs (§6)

- Sonnet agents of ≤3 turns: median $0.0876 → $0.0817, so Sonnet runners **$50–66 → $47–62/wk**.
  Haiku runners unchanged ($3–8/wk; 36k context stays under the 100k tier).
- Extra rounds: 13–67 × $0.42–0.69 → × $0.40–0.68: **$5–43 → $5–42/wk**.
- Round ≥2 coders: mean $1.52 → $1.46, median $0.78 → $0.64.

### 2.5 Lever table (§7)

| Lever | Before | After |
| --- | --- | --- |
| 1 Orchestrators and drivers become code | base $231.3; **$160–184/wk** (vs sketch $140–165: "slightly ADJUSTED up") | base $195.0; 75–87 % → **$135–156/wk** (now slightly **below** the sketch) |
| 2 No LLM waits | $61.9; **$40–57** | $63.2; **$41–58** |
| 3 Shorter coder contexts | **$15–40** | **$14–32** |
| 4 Bounded main session | **$65–105** | **$65–105** (unchanged) |
| Gross | $280–386 | **$255–351** |
| Overlap 3–8 % | −$10–30 | −$8–28 |
| Runners (Haiku) | −$3–8 (Sonnet −$50–66) | −$3–8 (Sonnet −$47–62) |
| Supervision | −$3–10 | −$3–10 |
| Extra rounds | −$5–43 | −$5–42 |
| **Net** | **$189–365/wk = 12–23 % of $1,573** | **$167–332/wk = 13–25 % of $1,325** |
| Factory scope (gross / net) | $193–258 / $117–242 | ≈ $173–234 / ≈ $98–218 [E, rescaled per lever] |
| Per CR, runs 1–3 | today $3.72–6.93; sketch $2.27–4.99; cut 18–39 % | today **$3.09–5.50**; sketch $1.82–3.95; cut **19–41 %** |

Verdict: still **CONFIRMED on the net share** (13–25 % vs the sketch's 10–22 %); the dollar
saving drops by $22–33/wk because the base is 16 % smaller. Lever 1 moves from "slightly up" to
"slightly down" against the sketch (the sketch's own $167 base may share the same price error).

## 3. A1 (`research2/A1-orchestration-costs.md`)

### 3.1 Key numbers (§0)

| Item | Before | After |
| --- | --- | --- |
| Orchestration roles today | $233.6 window, $214.9/wk: Foreman $116.1, Driver $84.2, stack $23.3, task $8.5, integrator $1.5 | **$197.1 window, $181.3/wk**: Foreman $97.1, Driver $76.6, stack $15.0, task $7.3, integrator $1.1 |
| Main session `dd375646` | $198.8 window, $182.9/wk; orchestration $84.9 | unchanged (Opus) |
| Rebuild writes, share of cost | Foreman 50 % ($58.1), Driver 42 % ($35.7) | Foreman **60 %**, Driver **47 %** (same $) |
| Waits outside the LLM alone, 5-min TTL | −$2.7 to +$3.4 window ("≈ $0") | **−$5.3 to −$0.4: a loss in both cases** |
| Same with 1-h TTL | +$21.9–26.1 ($20–24/wk) | +$20.1–23.1 ($18–21/wk) |
| Orchestration roles, design 2 | $126.1 – $76.4 window; saving $99–145/wk | **$105.4 – $66.6; saving $84–120/wk** |
| Main session, design 2 | $122.5 – $84.5; $70–105/wk | unchanged |
| Moved work | +$18–37/wk [E] | kept (≈ +$15–31 if scaled to the cheaper post-lever turns) |
| **Total net, this scope** | **$132–231/wk, 33–58 % of $398/wk; 8–15 % of $1,581/wk** | **$117–207/wk, 32–57 % of $364/wk; 9–16 % of $1,333/wk** |
| Per CR, runs 1–3 | $6.93 → $6.00–5.14; $4.86 → $4.62–4.19; $3.72 → $3.19–2.37 (5–36 %) | **$5.50 → $4.76–4.05; $3.54 → $3.34–3.03; $3.09 → $2.59–1.87 (6–39 %)** |
| Model | Sonnet everywhere −$5–9/wk; Haiku −$66–113/wk | **Sonnet −$7–12.5/wk; Haiku −$57–87/wk** (tier now applied) |

Simulator validation: baseline $236.37 vs $233.59 billed → $200.05 vs $197.14 (+1.5 %).

### 3.2 Levers in sequence (§9.1), window $

| Step | Conservative before → after | Optimistic before → after |
| --- | --- | --- |
| Simulated baseline | 236.37 → 200.05 | 236.37 → 200.05 |
| L2 waits | −5.6 → −2.0 | −11.3 → −6.4 |
| L3 `crf` collapses | −8.6 → −6.0 | −76.9 → −57.1 |
| L4a/b caps | −13.0 → −11.3 | −14.7 → −13.5 |
| L4c rotation | −44.0 → −34.6 | −19.2 → −17.3 |
| L5 1-h TTL (opt.: + re-arm) | **126.05 → 105.43** (−39.2 → −40.8) | **76.42 → 66.56** (−37.7 → −39.3) |
| L6 Sonnet | 116.84 → 91.85 (−9.2 → **−13.6**) | 71.26 → 58.94 (−5.2 → **−7.6**) |

Real $ of the dropped mechanical turns (§4): low $5.7 → $3.8, high $55.3 → $38.6 (Foreman high
$30.50 → $21.14). Factory scope: real $160.6 → $135.9 ($147.7 → $125.0/wk); design 2
$97.5 / $65.8 → $81.9 / $58.0; saving **$58–87/wk → $50–72/wk**. Runs 1–5: $66.8 →
$48.6 / $31.6 becomes $54.7 → $40.0 / $27.5.

### 3.3 Per role, per week (§9.2)

| Role | Today /wk | Design 2 /wk | Saving /wk |
| --- | --- | --- | --- |
| Foreman | $106.8 → **$89.3** | $45.6–25.9 → $37.7–22.3 | $61–81 → **$52–67** |
| Driver (CR) | $77.5 → $70.4 | $49.1–32.9 → $43.5–29.8 | $28–45 → $27–41 |
| Stack driver | $21.5 → $13.8 | $13.0–4.7 → $8.9–3.4 | $8–17 → $5–10.5 |
| Task driver | $7.8 → $6.8 | $6.7–5.9 → $5.6–5.0 | $1–2 → $1.1–1.7 |
| Integrator | $1.4 → $1.0 | $1.5–0.8 → $1.2–0.7 | −0.1/+0.5 → −0.2/+0.3 |
| **Orchestration, gross** | **$214.9 → $181.3** | $116.0–70.3 → **$97.0–61.2** | **$99–145 → $84–120** |
| Main session | $182.9 | $112.7–77.8 | $70–105 (unchanged) |
| **Total net** | $397.8 → **$364.2** | | **$132–231 → $117–207** |
| Optional Sonnet everywhere | | | +$5–9 → **+$7–12.5** |

### 3.4 TTL per role after levers 2–4 + rotation (§6), window $, conservative / optimistic

| Role | 5-min | 5-min + re-arm 4.5 min | 1-h | 1-h + re-arm 59.5 min | Best before → after |
| --- | --- | --- | --- | --- | --- |
| Foreman | 64.0/41.3 → 56.3/38.1 | 55.3/37.2 → 41.9/29.4 | 49.6/31.6 → 41.0/27.8 | 45.2/28.2 → **36.4/24.2** | 1-h + re-arm (same) |
| Driver | 76.3/55.9 → 70.9/53.1 | 54.0/39.1 → **45.5**/33.6 | 53.4/37.1 → 47.3/33.8 | 52.0/35.8 → 45.9/**32.5** | 1-h + re-arm → **5-min + re-arm (conservative)**, 1-h + re-arm (optimistic) |
| Stack driver | 15.0/8.5 → 10.6/7.2 | 13.8/6.6 → **8.8**/4.3 | 14.2/5.6 → 9.6/4.2 | 13.7/5.1 → 9.2/**3.7** | 1-h + re-arm → **5-min + re-arm (conservative)** |
| Task driver | 8.5/7.6 → 7.4/6.7 | 6.9/6.2 → **5.3/4.8** | 7.3/6.6 → 6.1/5.6 | 7.2/6.5 → 6.0/5.5 | 5-min + re-arm (same) |
| Integrator | 1.4/0.8 → 1.0/0.65 | 1.4/0.7 → 1.0/**0.59** | 1.7/0.9 → 1.3/0.8 | 1.7/0.9 → 1.3/0.8 | 5-min (same) |
| **All** | 165.2/114.1 → 146.2/105.8 | 131.4/89.8 → **102.4/72.7** | 126.1/81.8 → **105.4/72.2** | 119.7/76.4 → **98.8/66.6** | |

- The "practical point" gets stronger: **5-min TTL + `crf wait` re-arm ($102/$73) now matches a
  plain 1-h TTL ($105/$72)** and is within $4–6 of 1-h + re-arm. Before, a plain 1-h TTL was
  $5–8 cheaper than it, and 1-h + re-arm $12–13 cheaper.
- 1-h TTL alone today: −$65 window ($60/wk) → −$68 ($63/wk); Foreman −$40.6 → −$42.6, Driver
  −$23.3 → −$23.8.
- §3 poll arithmetic: a warm poll costs 0.08× → **0.04×** the 5-min write on Sonnet; polling every
  4.5 min beats one rebuild for waits under ≈55 min → **≈110 min**. Waits outside the LLM at a
  5-min TTL now always cost more ($0.4–5.3); in runs 1–5 they add $1.1–1.5 (was $0.2–0.9).

### 3.5 Small contexts (§5), Δ window $ (low / high)

| Sub-lever | Foreman 5-min | All roles 5-min | All roles 1-h |
| --- | --- | --- | --- |
| Hand-back cap 300 | −11.4/−9.3 → −9.3/−8.3 | −14.8/−12.5 → −12.6/−11.4 | −8.1/−5.7 → −5.6/−4.3 |
| Hand-back cap 600 | −6.7/−5.4 → −5.5/−4.9 | −8.8/−7.4 → −7.5/−6.7 | −4.7/−3.3 → −3.3/−2.5 |
| `crf status` | −3.2/−0.9 → −2.8/−0.8 | −5.8/−2.2 → −5.2/−2.1 | −3.8/−1.3 → −3.1/−1.1 |
| Rotation 60k | −43.0/−19.9 → −32.5/−17.2 | −52.7/−25.0 → −38.7/−22.0 | +10.4/+13.7 → **+26.0/+17.7** |
| Rotation 100k | −47.2/−22.7 → −37.1/−20.0 | −63.3/−28.3 → −50.3/−25.4 | −24.4/−4.9 → **−10.2/−1.3** |
| Rotation 150k | −39.9/−18.3 → −31.2/−16.3 | −52.2/−19.2 → −41.3/−17.2 | −23.6/−4.2 → −11.6/−1.6 |
| Compaction 100k | −49.6/−23.9 → −39.1/−21.0 | −66.8/−30.2 → −53.2/−27.0 | −27.1/−6.1 → −12.2/−2.1 |
| Compaction 150k | −41.4/−19.2 → −32.4/−17.0 | −54.3/−20.2 → −42.9/−18.0 | −24.7/−4.9 → −12.3/−2.1 |

Under a 1-h TTL the cap is now worth only $1–12 (was $4–27), and 100k vs 150k is a wash. 100k
stays best at a 5-min TTL.

### 3.6 Model per role (§7), window $

| Scenario | Before | After |
| --- | --- | --- |
| Today, simulated | 117.0 / 85.1 / 24.1 / 8.7 / 1.5 = 236.4 | 98.0 / 77.5 / 15.8 / 7.6 / 1.1 = **200.1** |
| Same tokens, all Sonnet | 111.2 / 68.6 / 24.2 / 9.0 / 1.6 = 214.6 (−$20/wk) | 91.4 / 56.9 / 15.9 / 7.9 / 1.2 = **173.3 (−$25/wk)** |
| Same tokens, all Haiku | 5.6 / 3.4 / 1.2 / 0.5 / 0.1 = **10.7 (flat price: wrong)** | 23.9 / 5.9 / 4.7 / 0.5 / 0.1 = **35.0** (>100k tier) |
| After levers → Sonnet (cons.) | Foreman 49.6 → 45.2, Driver 53.4 → 47.8; −$9.2 | Foreman 41.0 → 35.8, Driver 47.3 → 38.3; **−$13.6** |
| After levers → Sonnet (opt.) | Foreman 28.2 → 25.8, Driver 35.8 → 32.4; −$5.2 | Foreman 24.2 → 21.3, Driver 32.5 → 27.1; **−$7.6** |
| After levers → Haiku | opt. $3.8; cons. "≈ 1/20 of Sonnet" [E] → −$66 to −$113/wk | opt. $4.5; cons. **$10.9 simulated (1/8.5 of Sonnet)** → **−$57 to −$87/wk** |
| Main session on Sonnet, same tokens | $144.2 instead of $198.8 | **$99.4** (exactly half) |

## 4. A2 (`research2/A2-worker-costs.md`)

### 4.1 Role costs and anatomy (§0–§1)

| Role | Cost | Cache read | Output share | Opus share of $ | Thinking share of cost |
| --- | --- | --- | --- | --- | --- |
| Coder | $636.2 → **$528.6** | $344.1 → $236.5 | 16 % → 19 % | 44 % → 53 % | 9 % → 11 % ($59.8) |
| Inspector | $93.9 → $85.2 | $33.5 → $24.7 | 18 % → 20 % | 49 % → 54 % | 11 % → 12 % ($10.3) |
| Writer (req) | $139.5 → $108.5 | $66.1 → $35.2 | 23 % → 30 % | 9 % → 11 % | 12 % → 16 % ($17.4) |
| Critic (req) | $127.5 → $90.9 | $73.2 → $36.6 | 17 % → 24 % | 0 % | 11 % → 16 % ($14.2) |
| Analyst (req) | $174.2 → $128.1 | $102.4 → $56.3 | 15 % → 20 % | 10 % → 14 % | 8 % → 12 % ($14.8) |
| Analyst (other) | $17.1 → $16.8 | $4.6 → $4.2 | 32 % → 33 % | 46 % → 47 % | – |
| Conflict fixer | $3.2 → $2.7 | $1.2 → $0.7 | 7 % → 9 % | 28 % → 33 % | ≈0 |
| **All workers** | **$1,191.6 → $960.8** | | | | "6–11 %" → **11–16 %** |

Factory scope: coders $419.3 → $342.9, inspectors $52.1 → $47.4, conflict fixers $3.2 → $2.7.

### 4.2 Prefix and card cuts (§1.2), window $

| Role | Card −30 / −50 % | `Artifact` | Agent/List/Report tools | Skill listing | AGENTS + MEMORY | **All prefix cuts** |
| --- | --- | --- | --- | --- | --- | --- |
| Coder | 3.0/5.1 → 2.4/3.9 | 50.3 → 35.9 | 5.1 → 3.6 | 16.8 → 12.0 | 9.9 → 7.0 | **86.4 (13.6 %) → 63.0 (11.9 %)** |
| Inspector | 0.3/0.6 → 0.3/0.5 | 9.4 → 7.0 | 1.0 → 0.7 | 3.2 → 2.4 | 1.9 → 1.4 | 19.9 (21 %) → 16.0 (19 %) |
| Writer | 0.8/1.3 → 0.6/1.0 | 10.7 → 6.3 | 1.8 → 1.1 | 3.5 → 2.0 | 2.1 → 1.3 | 19.8 (14 %) → 12.4 (11 %) |
| Critic | 0.3/0.4 → 0.2/0.3 | 10.3 → 5.6 | 1.8 → 1.0 | 3.4 → 1.8 | 2.0 → 1.1 | 18.8 (15 %) → 10.9 (12 %) |
| Analyst (req) | 0.8/1.4 → 0.6/0.9 | 8.9 → 5.5 | 1.5 → 0.9 | 2.9 → 1.8 | 1.8 → 1.1 | 15.5 (9 %) → 9.7 (8 %) |
| **All workers** | **5.4/9.0 → 4.1/6.9** | **91.6 → 62.0** | 11.5 → 7.4 | 30.4 → 20.6 | 18.0 → 12.2 | **164.3 (13.8 %) → 115.3 (12.0 %)** |

Key finding 1 ("$151–164 in the window") becomes **≈ $106–115**.

### 4.3 Waits and long-suite options (§2)

- §2.1 excess: coder long suite $41.75 → $42.40 (pass $20.0 → $20.3, fail $21.7 → $22.1); CI
  $9.94 → $10.26; background $5.49 → $5.69; kept alive $6.82 → $7.12; other $10.29 → $10.60;
  fast gates $3.50 → $3.55; inspector suites $3.01 → $3.14, kept alive $2.83 → $2.95; analyst
  kept alive $13.65 → $14.25; writer kept alive $7.55 → $7.88. Event base coder $57.2 → $58.4,
  inspector $3.0 → $3.1. Factory share $31.85 → $32.41.

| Option (§2.2) | Coder before → after | Inspector before → after |
| --- | --- | --- |
| (a) background + notify | $0 | $0 |
| (b) 1-h TTL today | **−$12.7 → −$14.5** (cheaper) | +$16.6 → +$16.3 |
| (b) 1-h TTL after waits removed | +$43.1 → +$42.4 | +$19.6 → +$19.4 |
| (c) driver runs suite, resume coder | pass +$25.6 → +$26.1; driver −$17.1 → −$16.5; resume −$9.3 → −$9.0; net ≈ +$7–9 → ≈ +$8–10 | +$2.1 → +$2.2 pass; −$1.8 → −$1.7 driver |
| (c) fresh coder + note on failure | fail events $52–55 → **$43–45**; net ≈ $70 → ≈ $61 | +$0.4 → +$0.1 |
| (d) suites under ≈4.5 min | $40.0–41.0 → $40.5–41.6 | $2.6 → $2.7 |

- Driver cost per event $0.148 → $0.142. Resume rebuild per failure $0.57 → $0.58 (Sonnet
  ≈ $0.36 → $0.37, Opus $0.74 unchanged). Fresh coder: cold start $0.045–0.065 → $0.043–0.061;
  Sonnet re-exploration $0.18–0.22 → $0.15–0.17 (Opus $0.57–0.62 unchanged); fresh total
  $0.25–0.70 → **$0.19–0.70**. Fresh still cheaper or equal.
- TTL for writer / critic / analyst: +$11.2 / +$15.5 / +$4.8 → +$10.9 / +$15.4 / +$4.2 (still no).

### 4.4 Context levers (§3)

- Targeted reads / output cap / images: coder $8.1 / $7.6 / $3.8 → $7.3 / $6.1 / $3.0; inspector
  $1.8 / $4.4 / $0.9 → $1.7 / $4.0 / $0.9; writer $2.7 / $6.0 → $1.8 / $4.5; critic $4.6 / $4.4 →
  $2.9 / $3.1; analyst $8.9 / $2.8 → $5.8 / $2.1. Unchanged re-reads $1.2 → $0.9.
  Key finding 5 ("$15–30 a window") → ≈ **$12–23**.
- Resume vs fresh (cold resumes, fresh + note): coders $7.6 → $6.7, writers $6.3 → $5.8,
  inspectors $3.3 → $2.9, critics $1.2 → $1.4; **analysts −$0.4 → +$3.9** (without note −$19.6 →
  −$9.1). Hand-over note: $18.65 → $17.80 base, $4.7–9.3 → $4.5–8.9.
- Context cap 150k: coder −$85.9 (13.5 %) → **−$57.5 (10.9 %)**; analyst −$46.8 (27 %) →
  **−$20.8 (16 %)**; critic −$19.4 → −$7.1; writer −$15.4 → −$6.8; inspector ≈0.
  Cap 100k: coder −$96.0 → −$51.6, analyst −$47.8 → −$16.9, critic −$18.3 → −$1.6,
  writer −$12.5 → $0.

### 4.5 Inspector (§4)

Median $0.212 → $0.176 per agent (mean $0.398 → $0.361); factory median $0.191 → $0.160.
Diff-plus-note: $27.4 vs $93.9 → $25.5 vs $85.2 (factory $20.9 vs $52.1 → $19.4 vs $47.4),
saving $66 → $60. Sonnet inspectors $0.27 → $0.22 each (Opus $0.85 unchanged). Verdict schema
$1.3 unchanged (output only).

### 4.6 Model per role (§5), window $

| Role | Today | All Sonnet (Δ) | All Opus | All Haiku (tier, correct) | Haiku vs today |
| --- | --- | --- | --- | --- | --- |
| Coder | $636.2 → $528.6 | $559.8 (−$76) → **$387.8 (−$141)** | $775.5 | $109.9 | 5.8× → 4.8× cheaper |
| Inspector | $93.9 → $85.2 | $79.1 (−$15) → **$62.3 (−$23)** | $124.7 | $7.8 | 12× → 11× |
| Writer | $139.5 → $108.5 | $135.6 → $102.6 | $205.1 | $22.8 | 6.1× → 4.8× |
| Critic | $127.5 → $90.9 | = | $181.9 | $23.2 | 5.5× → 3.9× |
| Analyst (req) | $174.2 → $128.1 | $172.2 → $120.6 | $241.2 | $39.7 | 4.4× → 3.2× |
| Conflict fixer | $3.2 → $2.7 | $2.9 → $2.3 | $4.5 | $0.14 | 23× → 19× |

- **"Opus and Sonnet reads cost the same ($0.20)" is false.** All-Sonnet is exactly 50 % of
  all-Opus; Opus → Sonnet saves **50 %** of an Opus coder's cost (was "about 27 %").
- Haiku is "roughly 5–15× cheaper" → **roughly 3–11× cheaper** than today's mix for the main
  roles. Above 100k, Haiku's read price ($0.05) is half Sonnet's, not a quarter.

### 4.7 Combined (§6–§7)

| Role | Window cost | Prefix | Card, reads, caps, images | Waits | Resume + note | **Window** | **Per week** | % of role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Coder | $636.2 → $528.6 | 74.8–80.9 → 54.1–58.8 | 11.4–25.1 → 9.4–20.7 | 7.4–59.8 → 8.3–55.2 | 8.1–16.0 → 7.5–14.9 | **102–182 → 79–150** | 94–167 → **73–138** | 16–29 → 15–28 % |
| Inspector | $93.9 → $85.2 | 16.0–18.1 → 12.6–14.4 | 3.4–7.6 → 3.2–7.1 | 0.4–2.1 → 0.5–2.2 | 1.3–2.4 → 1.2–2.2 | 21–30 → 17–26 | 19–28 → 16–24 | 23–32 → 20–30 % |
| Writer | $139.5 → $108.5 | 16.1–18.5 → 9.7–11.5 | 5.2–10.0 → 3.8–7.4 | – | 2.8–5.3 → 2.6–5.0 | 24–34 → 16–24 | 22–31 → 15–22 | 17–24 → 15–22 % |
| Critic | $127.5 → $90.9 | 15.3–17.6 → 8.6–10.2 | 4.8–9.5 → 3.2–6.4 | – | 0.6–1.0 → 0.6–1.2 | 21–28 → 12.5–18 | 19–26 → 11–16 | 16–22 → 14–20 % |
| Analyst (req) | $174.2 → $128.1 | 12.9–14.6 → 8.1–9.1 | 6.7–13.1 → 4.5–8.8 | – | – | 20–28 → 12.5–18 | 18–25 → 12–16 | 11–16 → 10–14 % |
| Analyst (other) | $17.1 → $16.8 | 2.2–2.4 → 2.1–2.3 | 0.2–0.4 → 0.2–0.3 | – | – | 2–3 → 2.3–2.6 | 2–3 → 2 | 14–16 % |
| Conflict fixer | $3.2 → $2.7 | 1.0–1.1 → 0.7–0.8 | 0.1–0.2 → 0.1 | – | – | 1.0–1.2 → 0.8–0.9 | ≈ $1 | 33–39 → 28–34 % |
| **All workers** | **$1,191.6 → $960.8** | | | | | **$191–306 → $141–239** | **$175–281 → $130–219** | **16–26 → 15–25 %** |

- Factory-scope workers: $475.2 → $393.5; saving $79–130 (17–27 %) → **$60–104 (15–26 %)**.
- Optional levers (window): cap 150k coder $86 → $58, analyst $47 → $21, critic $19 → $7,
  writer $15 → $7; all-Sonnet coders **$76 → $141**, Sonnet inspectors $15 → $23; Haiku
  inspectors $70–86 → $55–77; conflict fixers $3 → $2.6; effort −30 % $35 unchanged; diff-only
  inspector $66 → $60. Waits column overlapping lever 2: $7–62 → $9–57 (base $57 → $58).
- §6 table: prefix cuts writer $16–19 → $10–11.5, critic $15–18 → $8.6–10, analyst $13–15 →
  $8–9; Haiku $23 vs $140 → $23 vs $109 (writer), $23 vs $128 → $23 vs $91 (critic), $40 vs
  $174 → $40 vs $128 (analyst).

### 4.8 Per CR, runs 1–3 (§7)

The A2 script hard-coded the old all-in $/CR; corrected values are from design-1 §2.1.

| Run | Worker $/CR | Saving/CR | All-in $/CR today | Cut of all-in |
| --- | --- | --- | --- | --- |
| 1 | $4.44 → $3.48 | $0.73–1.01 → $0.50–0.73 | $6.93 → $5.50 | 10–15 % → **9–13 %** |
| 2 | $3.70 → $2.61 | $0.50–0.74 → $0.30–0.51 | $4.86 → $3.54 | 10–15 % → **8–14 %** |
| 3 | $1.66 → $1.24 | $0.38–0.45 → $0.24–0.30 | $3.72 → $3.09 | 10–12 % → **8–10 %** |

## 5. Conclusions that flip or move materially

1. **Sonnet vs Opus (A2 §5, A1 §7):** "Opus and Sonnet reads cost the same, so Opus → Sonnet
   saves only ~27 %" is wrong. Sonnet 5.5 is half of Opus 5.5 on every token class. All-Sonnet
   coders save **$141**, not $76, in the window; main session on Sonnet would be $99.4, not $144.2.
   Opus is now 53 % of coder spend and 54 % of inspector spend.
2. **Haiku in A1 was priced without the >100k tier.** Same-token Haiku for orchestration roles is
   **$35.0, not $10.7**; after the levers the Haiku saving is **$57–87/wk, not $66–113/wk**, and
   the conservative case is 1/8.5 of Sonnet, not 1/20. A2's Haiku figures were already correct.
3. **TTL per role (A1 §6):** in the conservative case, Driver and stack driver flip from
   "1-h + re-arm" to **"5-min + re-arm"**. A 5-min TTL with a `crf wait --max 270s` re-arm now
   matches a plain 1-h TTL for all orchestration roles ($102/$73 vs $105/$72).
4. **Waits outside the LLM at a 5-min TTL (A1 §3):** was "≈ $0 (−$2.7 to +$3.4)"; now a **loss
   in both cases (−$0.4 to −$5.3)**. Warm polls are half the price, so keep-warm polling is
   cheaper than a rebuild for waits up to ≈110 min.
5. **Analyst resume rule (A2 §3.4, §6, key finding 3):** "analysts lose with fresh agents, always
   resume them" flips: fresh + note when cold now **saves $3.9**; only fresh without a note still
   loses.
6. **Context cap (A2 §3.4, §7):** analyst 150k cap 27 % → **16 %**; coder 13.5 % → 10.9 %;
   writer and critic caps become marginal ($7). At 1-h TTL (A1 §5) rotation is worth $1–12, not
   $4–27; rotation at 60k is now clearly harmful (+$18–26).
7. **Design-1 lever 1** moves from "slightly above the sketch" ($160–184) to slightly **below**
   it ($135–156/wk). The net saving falls to **$167–332/wk** but its share rises to **13–25 %**
   of a smaller week ($1,325). Verdict still CONFIRMED.
8. **Unchanged verdicts:** design-1 1-h TTL (today −$34 window, after levers +$85/wk: rejection
   holds); Haiku runner still required (Sonnet runner −$47–62/wk); lever 2 ($41–58/wk); lever 4
   and the whole main-session analysis (Opus); A2 coder 1-h TTL still a stop-gap (−$14.5) and
   dearer for every other worker role; fresh coder on failure still beats resume.
9. **Rebuilds weigh more:** rebuild excess is 48 % of orchestration own cost (was 40 %); rebuild
   writes are 60 % of Foreman cost (was 50 %). The levers that shrink the context at the wake
   matter relatively more; cache-read-driven levers (prefix cuts, read caps, context caps)
   matter less, by about a third.
