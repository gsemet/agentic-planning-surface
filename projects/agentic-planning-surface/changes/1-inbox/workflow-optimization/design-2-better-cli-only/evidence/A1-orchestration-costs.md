# A1 — Orchestration roles under design 2: measured cost and simulated levers

- **Date:** 2026-10-27. Data snapshot: last turn 2026-10-27T22:13Z (run 4/5 still running).
- **Scope:** Foreman (today's orchestrator), Driver and its variants (stack driver, task driver,
  integrator), and the main session `dd375646-4450-4e52-a643-89ff1d9e405a` as Chief of Staff.
  Coders and reviewers are out of scope; they keep their real cost in every figure below.
- **Question:** design 2 keeps every layer as an LLM agent. What can tools (`crf`), waits outside
  the LLM, small contexts, TTL and model choice save, measured on real turn sequences?
- **Labels:** **[M]** measured from transcripts, **[S]** simulated on the real turn sequences,
  **[E]** estimated (method stated). "Window" = 7.61 active days; "/wk" = window × 0.92.

## 0. Key numbers

| Item | Value |
| --- | --- |
| Orchestration roles today | **$233.6 window, $214.9/wk** [M]: Foreman $116.1, Driver $84.2, stack $23.3, task $8.5, integrator $1.5 |
| Main session `dd375646` today | **$198.8 window, $182.9/wk** [M]; its orchestration turns **$84.9 (43 %)** [M] |
| Biggest cost driver in Foreman/Driver | **Cache rebuilds after waiting for a child**: rebuild writes are 50 % of Foreman cost ($58.1) and 42 % of Driver cost ($35.7) [M]; the trigger is mostly a child's hand-back (Foreman 61 rebuilds $30.9, Driver 88 rebuilds $23.9) [M] |
| Lever "waits outside the LLM" alone | **≈ $0 at 5-min TTL** (−$2.7 to +$3.4 window) [S]: today's polls keep the cache warm. It pays only with a 1-h TTL or keep-warm re-arm ($20–24/wk) [S] |
| Lever with the largest effect | **Small contexts + cache policy**: rotation/compaction at 100k plus 1-h TTL (or keep-warm ticks) [S] |
| Orchestration roles, design 2 | **$126.1 (conservative case) to $76.4 (optimistic case) window** [S] → saving **$99–145/wk** gross [S] |
| Main session, design 2 | **$122.5 to $84.5 window** [S, scaled] → saving **$70–105/wk** [S]; **$78–113/wk remains** [S] |
| Work moved from main to Foreman/Driver | **+$18–37/wk** [E] |
| **Total net saving, this scope** | **$132–231/wk** [S+E]: 33–58 % of the in-scope $398/wk, **8–15 % of the whole measured week** ($1,581/wk [M]) |
| Per CR, runs 1–3 (orchestration + main only; coders unchanged) | run 1 $6.93 → $6.00–5.14; run 2 $4.86 → $4.62–4.19; run 3 $3.72 → $3.19–2.37 (**5–36 % cut**) [S] |
| Model | Sonnet everywhere adds −$5–9/wk after the other levers [S]; Haiku −$66–113/wk [S] but quality is not measured and Foreman contexts exceed 200k today |

The ranges come from two simulated cases, each applying the levers **in sequence** on the real
turns. The conservative case uses narrow lever definitions; the optimistic case uses broad ones (§9).

## 1. Method

- **Data [M].** I re-extracted the per-turn data with design-1 `extract.py`, copied unchanged:
  958 agents, $1,719.2, 33,154 turns.
  - This is design-1's $1,705.5 plus 25 minutes of run 4/5.
  - Same dedupe (`message.id`), same exclusions (`c985a2ca…`, `<synthetic>`), same prices (01-costs §1).
  - Opus 4/5/8/0.20/20, Sonnet 2/2.5/4/0.20/10, Haiku 0.10/0.125/0.20/0.01/0.50 $/MTok
    (input, 5-min write, 1-h write, read, output).
- **Roles [M].** Roles come from design-1 `common.role()`. "Main" is only `dd375646`. The other
  12 main sessions are out of scope.
- **Turn simulator [S]** (`a1_sim.py`). Each lever transforms the real turn sequence of each agent:
  - it drops turns, caps the tokens that enter the context, or rotates or compacts at a cap;
  - the simulated context is S_i = real context minus the tokens removed so far;
  - each kept turn costs:
    - a write of S_i on the first turn or after a gap longer than the TTL;
    - otherwise a read of S_prev plus a write of the growth;
    - plus output.
  - The gap is measured from the last kept turn's end to this turn's start.
  - A rebuild reads the shared 19.7k system and tools prefix when a sibling keeps it warm. The
    probability of that is measured per role.
  - **Validation:** the baseline simulation lands within **+1 % to +3 %** of the billed cost for
    every orchestration role (Foreman $116.98 vs $116.06; Driver $85.06 vs $84.22; stack
    $24.11 vs $23.34; task $8.73 vs $8.48; integrator $1.50 vs $1.50).
  - For the main session, `a7_main.py` uses its own variant with compactions. It simulates
    $207.4 vs $198.8 billed (+4 %), so main-session savings are scaled by 0.958.
- **Tokens from characters [M, calibrated].** 2.4 characters per token: the median context growth
  per character on 881 turns with more than 20k characters of new input (`a1_calib.py`).
- **Scripts and outputs:** `research2/scripts/A1/` (`a1_*.py`, `a2_waits.py`, `a3_mech.py`,
  `a4_small.py`, `a5_ttl.py`, `a7_main.py`, `a8_combine.py`; raw output in `out/*.txt`).
  The design-1 originals were copied, never modified.

## 2. Anatomy per role [M]

| Role | Agents | Turns | Cost | Model $ | Read | 5-min write | Output | Context median / p90 / max | First-turn context | Growth per turn (median) | Rebuilds 5–15 / 15–60 / >60 min | Rebuild write $ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Foreman (orchestrator) | 31 | 1,189 | $116.06 | Sonnet 102, Opus 14 | 39.8 | 66.5 | 9.8 | 129k / 410k / 494k | 33k | 2.3k | 58 / 42 / 15 | **$58.05** |
| Driver (CR) | 95 | 2,026 | $84.22 | Opus 44, Sonnet 40 | 23.6 | 51.5 | 9.2 | 58k / 93k / 211k | 34k | 1.8k | 82 / 45 / 6 | **$35.74** |
| Stack driver | 5 | 620 | $23.34 | Sonnet | 16.6 | 4.6 | 2.1 | 101k / 267k / 311k | 35k | 0.9k | 3 / 1 / 2 | $3.02 |
| Task driver | 25 | 273 | $8.48 | Sonnet | 2.3 | 5.0 | 1.2 | 50k / 59k / 70k | 35k | 1.7k | 16 / 4 / 1 | $2.16 |
| Integrator | 5 | 88 | $1.50 | Sonnet | 0.8 | 0.5 | 0.2 | 47k / 54k / 57k | 35k | 1.1k | 0 | 0 |
| Main `dd375646` | 1 | 2,391 | $198.78 | Opus, 1-h cache | 89.6 | 1-h writes 77.5 | 31.7 | 184k / 321k / 501k | – | – | 1 / 0 / 29 (>1 h) | $46.09 |

- **Subagents never compact** [M]: 0 compactions in 157 orchestration agents. The main session
  compacted 17 times.
- **Runs 1–5 only** [M]:
  - Foreman: 4 agents, $15.89, median context 96k.
  - Drivers: 46 agents, $17.97, median context 52k.
  - Stack drivers: 4 agents, $22.04, median context 109k.
- **First turn [M].**
  - It is 33–35k tokens: the system prompt and tools (19.7k, often shared and cached), the
    skill, and the brief.
  - The brief itself is small: median 1,055 tokens (Foreman) and 703 tokens (Driver).
  - Skill and brief reads after the first turn add 3.0–3.3k tokens each: 84 reads in Foremen,
    268 in Drivers.
- **Top agents [M]:**

  | Agent | Role | Cost | Turns | Context median / max | Notes |
  | --- | --- | --- | --- | --- | --- |
  | `aa284441fb21ed442` | P1+P2 orchestrator | $40.03 | 285 | 264k / 453k | 36 rebuilds |
  | `a14fa7d64e7b029f2` | Orchestrator L | $25.11 | 230 | 342k / 494k | – |
  | `a3a9ea083fe2f3289` | Driver CR 056, Opus | $20.39 | 96 | 131k | 24 rebuilds |
  | `a05ca1697b4543086` | Stack driver 107–120 | $16.90 | 324 | 198k | – |
  | `a35435560038683fc` | Orchestrator K | $16.84 | 138 | 284k | – |
  | `a7dc8322f1d2b1eb9` | Run-1 orchestrator | $6.97 | 66 | 122k / 151k | 19 rebuilds |

### 2.1 What the context is made of [M, carry model]

Each item is written once, then read on every later turn. "Carry $" is that write plus the reads,
until the end of the agent.

| Role | Hand-back reports | Brief/skill reads | Status reads | git/gh output | Poll output | Own output carried | Total cache read |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Foreman | 498 × 884 tok, carried 85 turns: **$8.75** | 84 × 3,047 tok: $3.46 | 59 × 1,761 tok: $1.29 | 150 × 566–652 tok: $1.32 | 82 × 157 tok: $0.22 | **$12.02** | $39.82 |
| Driver | 223 × 929 tok, 21 turns: $1.68 | 268 × 3,255 tok: **$5.97** | 81 × 752 tok: $0.51 | 460 × 497–578 tok: $1.90 | 414 × 132 tok: $0.40 | $1.93 | $23.58 |
| Stack driver | 30 × 767 tok: $0.35 | 12 × 2,974 tok: $0.98 | 21 × 336 tok: $0.19 | 153 tok: $1.25 | 72 × 163 tok: $0.15 | **$4.97** | $16.60 |
| Main | 20 × 1,071 tok: $0.64; task notifications 349 × 335 tok: $3.52 | 110 × 1,337 tok: $4.32 | 151 × 778 tok: $3.79 | 444 tok: $6.41 | 54 × 197 tok: $0.28 | **$28.35** | $89.60 |

- **Poll output is negligible.** What costs is the **number of turns** and the **context size at
  each wake**, not what each command prints.
- **Hand-backs are the Foreman's largest input** (884 tokens on average, carried 85 turns).
- **Spawn boilerplate is small** [M]. Foremen wrote 494 Agent prompts (median 343 tokens, 248k
  tokens in total) and Drivers wrote 231 (median 650, 180k in total), about **$5 of output in the
  window**. A `crf brief` that renders the prompt would save about $3–4 [E].

## 3. Lever "waits outside the LLM" (item 2)

Wait turns are turns whose tools are only polls, sleeps, `until` loops, `Monitor` or `TaskOutput`
(low definition). The high definition adds one-shot `gh run` or `gh pr checks` calls and "idle
ticks": a wake from a background sleep, status reads only, then a re-arm. An episode is a run of
consecutive wait turns. In design 2 it becomes one background `crf wait` call (150-token result),
and the next real turn is the **wake**. The wake is a rebuild at the agent's context when the wall
gap exceeds the TTL.

| Role | Wait turns (low–high) [M] | Their real cost [M] | Episodes; polls per episode | Episode wall time median / p90 [M] | Wakes after > 5 min [S] | Episodes incl. wake: real → design 2, 5-min TTL [S] | → design 2, 1-h TTL [S] |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Foreman | 78–85 | $8.5–9.5 | 53–55; median 1 (max 4) | 1.3–1.8 / 10.2 min | 14 | $16.6–17.3 → $14.1–14.4 | → $5.8–6.1 |
| Driver | 378–501 | $8.9–14.0 | 141–158; 2 (max 24) | 4.8 / 19–22 min | 54–62 | $16.8–18.9 → $17.3–19.3 | → $6.8 |
| Stack driver | 71–101 | $2.2–3.2 | 38–45; 1 (max 9) | 2.2–4.4 / 10 min | 9–11 | $3.5–4.7 → $5.0–6.1 | → $2.6–3.3 |
| Task driver | 7–8 | $0.1 | 2–3 | < 1 min | 0 | ≈ 0 | ≈ 0 |
| Main | 43–99 | $2.7–5.8 | 39–72; 1 | < 1 min | 1 | $5.0–10.1 → $6.2–9.8 | → $4.8–8.6 |
| **Total** | **≈ 580–790** | **$22–33** | | | | **$42.0–51.1 → $44.6–47.7 (−$2.7 to +$3.4)** | **→ $20.1–24.9 (+$21.9–26.1)** |

- **Finding [S]: at a 5-minute TTL, moving waits out of the LLM saves nothing.**
  - Each poll turn costs a warm read: 0.08× the 5-min write price on Sonnet.
  - One poll every 4.5 minutes is cheaper than one rebuild for any wait under about 55 minutes.
  - Today's skill already re-arms the Foreman's background wait every 270 s, and that is exactly
    this keep-warm effect.
  - In the sequential simulation, L2 alone saves $5.6–11.3 in the window. For runs 1–5 it
    *adds* $0.2–0.9 [S].
- **What pays [S]:** a `crf wait` that wakes on an event **or** at TTL − 30 s (a keep-warm re-arm).
  Alternatively, a 1-h TTL. Either one turns the wait saving into **$20–24/wk** (§6).
- **The real wait is for children, not for CI [M]:**
  - Most rebuilds follow a child's hand-back: Foreman 61 ($30.91), Driver 88 ($23.89).
  - Rebuilds after a foreground Bash call over 5 minutes: Foreman 38 ($23.40), Driver 71
    ($21.69). These overlap with the hand-back rebuilds.
  - These waits are already outside the LLM. Only the TTL policy and a smaller context at the
    wake reduce them.
- **For drivers, coders run the long suites.** Driver episodes are CI watches in slices of under
  5 minutes (median 4.8 minutes of wall time, up to 24 polls).

## 4. Lever "mechanical turns collapsed into `crf`" (item 3)

Turn classes come from design-1 `c_lever1.category()`. A run of consecutive mechanical turns becomes
one `crf` call that keeps the first turn's decision and returns 400 tokens. The low case collapses
only git/gh and status-write runs of 3 or more. The high case collapses every mechanical class
(reads, git/gh, status writes, gates) in runs of 2 or more.

| Role | `crf` calls (low / high) | Turns dropped [S] | Turns replaced per call (incl. the call) | Real $ of dropped turns [M] | Main commands (high: calls/dropped) |
| --- | --- | --- | --- | --- | --- |
| Foreman | 19 / 107 | 49 / 464 | 3.6 / 5.3 | $2.78 / $30.50 | `crf ship` 27/191, `set/render` 36/118, `status` 25/61, `gate` 10/43, `open/land` 6/36 |
| Driver | 32 / 194 | 79 / 512 | 3.5 / 3.6 | $1.67 / $12.27 | `ship` 48/137, `set/render` 52/124, `status` 58/126, `ci` 18/57, `gate` 14/61 |
| Stack driver | 14 / 51 | 40 / 330 | 3.9 / 7.5 | $1.09 / $11.02 | `ship` 17/145, `gate` 6/58, `status` 17/59, `stack` 5/30 |
| Task driver | 3 / 24 | 6 / 36 | 3.0 / 2.5 | $0.10 / $0.70 | `ship` 11/18 |
| Integrator | 2 / 10 | 7 / 54 | 4.5 / 6.4 | $0.10 / $0.77 | `ship` 4/36, `gate` 6/18 |

- **Per CR [M/S], high case:**
  - Runs 1–5 drivers (46): median 11 turns per CR, 5 of them mechanical. That gives **1.6 `crf`
    calls per CR replacing 3.3 turns**.
  - Pre-run-1 drivers (47): 22 turns per CR, 16 mechanical, **2.4 calls replacing 14.1 turns**.
- **Saving in sequence, after L2 [S]:**
  - **−$8.6 window in the low case, −$76.9 in the high case** ($8–71/wk).
  - In the high case, the saving exceeds the $55 cost of the dropped turns. The rest comes from the
    smaller context that every later turn carries, and it lands mostly on the large Foreman and
    stack-driver contexts.
  - The cost of the remaining `crf` call turn (decision, plus the 400-token result) is already
    inside the simulation.
- **Where the high case is optimistic.** It assumes the Foreman never needs to read a file beyond
  `crf` output. Many "reads" in Foremen K and L (requirements batches) were hand-back report files.
  The range is therefore wide on purpose.

## 5. Lever "small contexts" (item 4) [S]

Each sub-lever is applied alone on top of L2+L3 (low / high). Δ in $ for the window:

| Sub-lever | Foreman, 5-min TTL | All roles, 5-min TTL | All roles, 1-h TTL |
| --- | --- | --- | --- |
| (a) Hand-back capped at 300 tokens | −11.4 / −9.3 | **−14.8 / −12.5** | −8.1 / −5.7 |
| (a) Hand-back capped at 600 tokens | −6.7 / −5.4 | −8.8 / −7.4 | −4.7 / −3.3 |
| (b) `crf status` (400 tokens) replaces status reads and git/gh status output | −3.2 / −0.9 | −5.8 / −2.2 | −3.8 / −1.3 |
| (c) Rotation (fresh Foreman or Driver) at 60k | −43.0 / −19.9 | −52.7 / −25.0 | **+10.4 / +13.7** |
| (c) Rotation at 100k | −47.2 / −22.7 | **−63.3 / −28.3** | **−24.4 / −4.9** |
| (c) Rotation at 150k | −39.9 / −18.3 | −52.2 / −19.2 | −23.6 / −4.2 |
| (d) Auto-compaction at 100k | −49.6 / −23.9 | −66.8 / −30.2 | −27.1 / −6.1 |
| (d) Auto-compaction at 150k | −41.4 / −19.2 | −54.3 / −20.2 | −24.7 / −4.9 |

- **What a rotation costs in the model:** a handover turn of 800 output tokens; a fresh agent with
  the measured first-turn context, plus 9.5k tokens (the handover and a re-read of the skill and
  brief); and 3 re-read turns.
- **What a compaction costs in the model:** a 3.7k-token summary (the main session's measured
  summary size), then a cold prefix.
- **Rotation versus compaction:**
  - Rotation and compaction cost within ±$2 of each other at 100–150k.
  - At 60k, rotation is the worse choice: 178 rotations with cold starts.
  - Rotation keeps the "fresh Foreman per batch" property and needs the state in `crf`.
- **Best cap: 100k.** At a 1-h TTL, rotating at 60k costs more than not rotating.
- **Why it works:** contexts are large at the moments that matter. 37 % of Foreman turns run
  above 200k tokens (444 of 1,189), and so do 25 % of stack-driver turns (156 of 620). Every
  wake rebuilds that context [M].
- **Hand-back cap:** worth $5–15 in the window. The Foreman carries 498 hand-backs for 85 turns
  each.
- **`crf status` alone is small** ($1–6). Its value is in L3 (fewer turns) and in the main
  session (§8).

## 6. Lever "TTL" per role, after levers 2–4 (item 5) [S]

Gaps between kept turns after the high-case levers [S]:

| Role | Under 5 min | 5–15 min | 15–60 min | Over 1 h |
| --- | --- | --- | --- | --- |
| Foreman | 83 % | 8 % | 7 % | 2.3 % |
| Driver | 83 % | 9 % | 7 % | 0.7 % |
| Stack driver | 86 % | 9 % | 4 % | 0.9 % |
| Task driver | 85 % | 12 % | 2 % | 0.5 % |

Median of the gaps over 5 minutes: 9–17 minutes. These are the child rounds.

Cost after levers 2–4 plus rotation, window $ (conservative / optimistic case):

| Role | 5-min | 5-min + keep-warm re-arm every 4.5 min | 1-h | 1-h + re-arm every 59.5 min | Best |
| --- | --- | --- | --- | --- | --- |
| Foreman | 64.0 / 41.3 | 55.3 / 37.2 | 49.6 / 31.6 | **45.2 / 28.2** | 1-h + re-arm |
| Driver | 76.3 / 55.9 | 54.0 / 39.1 | 53.4 / 37.1 | **52.0 / 35.8** | 1-h + re-arm |
| Stack driver | 15.0 / 8.5 | 13.8 / 6.6 | 14.2 / 5.6 | **13.7 / 5.1** | 1-h + re-arm |
| Task driver | 8.5 / 7.6 | **6.9 / 6.2** | 7.3 / 6.6 | 7.2 / 6.5 | 5-min + re-arm |
| Integrator | **1.4** / 0.8 | 1.4 / **0.7** | 1.7 / 0.9 | 1.7 / 0.9 | 5-min |
| **All** | 165.2 / 114.1 | **131.4 / 89.8** | 126.1 / 81.8 | 119.7 / 76.4 | |

- **The 1-h TTL alone, today:**
  - With no other lever it saves **$65 window, $60/wk** on these roles [S]: Foreman −$40.6,
    Driver −$23.3.
  - Design-1 found a 1-h TTL across all sub-agents cheaper today (−$28) but more expensive once
    the coder levers are in place (+$87/wk, 01-costs §5.3).
- **Practical point.** The documented switch is one setting for all sub-agents
  (`subagentPromptCacheTtl`, 04-mechanisms C7); a per-agent TTL is not documented. If the TTL
  cannot be set per role, the **5-min TTL plus a `crf wait --max 270s` re-arm** captures most of
  the gain: $131 / $90 against $126 / $76 with a 1-h TTL. It leaves coders untouched.

## 7. Lever "model per role" (item 6) [S, same tokens; quality not measured]

| Scenario (window $) | Foreman | Driver | Stack | Task | Integrator | All |
| --- | --- | --- | --- | --- | --- | --- |
| Today, current mix (simulated baseline) | 117.0 | 85.1 | 24.1 | 8.7 | 1.5 | 236.4 |
| Same tokens, all on Sonnet | 111.2 | 68.6 | 24.2 | 9.0 | 1.6 | **214.6** (−$20/wk) |
| Same tokens, all on Haiku | 5.6 | 3.4 | 1.2 | 0.5 | 0.1 | 10.7 |
| After levers 2–5: current mix → Sonnet | 49.6 → 45.2 (conservative); 28.2 → 25.8 (optimistic) | 53.4 → 47.8; 35.8 → 32.4 | | | | −$9.2 (conservative), −$5.2 (optimistic) |
| After levers 2–5: Haiku | | | | | | $3.8 in the optimistic case [S]; conservative case ≈ 1/20 of Sonnet [E] → **−$66 to −$113/wk** |

- **What Sonnet changes:** Opus money in these roles is Driver $44 (CR 056 `a3a9ea083fe2f3289`
  $20.4, CR 041 `afbf80cc903eb7766`) and Foreman $14 (runs 3 and 4/5). The skill default is
  already Sonnet. After the other levers, Sonnet everywhere adds **$5–9/wk**.
- **Haiku is not feasible as-is.**
  - Foreman contexts exceed 200k on 444 turns, in 3 agents; stack drivers on 156 turns [M].
  - Haiku needs rotation at 150k or less.
  - Assumption, not checked: a 200k context window, as in Haiku 4.5.
- **Decisions at risk on a cheaper model** (from 03-judgment):
  - cross-CR regression attribution after a bisect (Part A row 12, 6 cases);
  - granting extra rounds and resuming after an API death (rows 8, 14);
  - stack reorder and base-cycle repair (row 11; the #128↔#129 cycle);
  - flaky versus real failures (row 2) and infra versus product CI failures (rows 1, 5);
  - accepting an evidence mismatch (row 13: the orchestrator accepted 115's mismatch);
  - semantic rebase conflicts in stack drivers (row 3: T11 mathRenderer, 051 extension.ts, 048);
  - for Drivers, when to escalate a coder to Opus.

  These are rare (a few per run) but drive per-CR cost: CRs 123, 115 and 131. Haiku is plausible
  for the task driver and the integrator only, since they make few judgment calls.
- **Main session on Sonnet at the same tokens:** $144.2 instead of $198.8 [S]. It is out of scope
  here, because the Chief of Staff holds the judgment.

## 8. Main session as Chief of Staff (item 7)

### 8.1 Why the main session did orchestration [M]

Orchestration turns use design-1 `f_lever4.mclass()`: 1,053 turns, **$84.91**, matching 01-costs
§5.4 ($84.68). Each episode (from a user message or a notification to the next one) gets one cause,
in priority order. The last column is the saving when only that cause's turns are dropped
[S, before the 0.958 scaling].

| Cause | Episodes | Turns | $ | Design-2 fix | Saving alone |
| --- | --- | --- | --- | --- | --- |
| A. Foreman or agent stalled, froze or died, or a message never arrived (nudges, 26 `TaskStop`, re-spawns) | 38 | 105 | $8.95 | Foreman heartbeat in `crf` (`crf status` flags a stale Foreman); `crf wait` also exits on a mailbox note, so messages land within one re-arm (today 16 of 89 messages to orchestrators were lost and 23 were more than 30 min late, 02-dynamics); `crf foreman restart` from state | $11.25 |
| B. User asked for status | 19 | 34 | $1.81 | one `crf status` call (about 400 tokens) | $2.58 |
| C. Merge and landing follow-up ("merged") | 34 | 99 | $8.31 | `crf wait` includes a merged-PR event, then the Foreman runs `crf land` and restacks; the main session does nothing | $8.31 |
| D. Report from a factory agent (77 orchestrator task notifications, 10 hand-backs, 17 driver notifications) | 63 | 109 | $8.29 | the Foreman notifies the main session only for a decision or at run end, with a short schema; drivers never notify the main session | $8.74 |
| E. The main session's own background CI, heavy-CI and bisect shells | 51 | 167 | $16.93 | the Foreman owns them (`crf ci wait`, `crf bisect`); the main session gets the verdict | $13.80 |
| F. The main session acted as orchestrator (93 coder and 71 reviewer notifications from agents it launched itself, before the factory) | 119 | 247 | $18.32 | always go through a Foreman or Driver, even for one CR | $24.31 |
| G. User decision or new work, then relay, brief, open CRs and re-check state | 112 | 292 | $22.31 | `crf note` / `add` / `grant` / `hold`; state re-checks become `crf status`; the judgment turns stay | $31.10 |

The "saving alone" column overlaps across causes. Those figures add up to $100, more than the
combined saving.

### 8.2 Simulated Chief of Staff [S, Opus, 1-h TTL, scaled to billed]

| Variant | What is dropped | Main session cost | Saving |
| --- | --- | --- | --- |
| Conservative | 415 orchestration turns; keeps relays, restarts and scripts in user episodes and the first turn of each notification episode; one `crf` call per status, merge or "continue" episode | $157.9 | $40.8 |
| + auto-compaction at 150k (23 compactions) | | **$122.5** | **$76.2 (≈ $70/wk)** |
| Optimistic | 911 turns (only relays of user decisions kept) | $118.5 | $80.2 |
| + auto-compaction at 100k (35 compactions) | | $99.2 | $99.5 |
| + keep-warm `/loop` tick every 59.5 min while the user is away | | **$84.5** | **$114.2 (≈ $105/wk)** |

- **Keep-warm ticks.** The main session sat idle for over 1 h 33 times (96.5 h in total, median
  1.5 h) [M], and each return rebuilt about 184k tokens of Opus at the 1-h write price. A
  59.5-minute tick costs a warm read instead. On today's session, ticks alone would save $40 in
  the window [S]; on top of the optimistic variant, $15. Two caveats: this assumes the session
  stays open, and ticks burn usage while the user is away.
- **What stays in the main session: $78–113/wk** [S]. That is user conversation, backlog and CR
  authoring, judgment, `crf note`/`status` calls, and reading the Foreman's decision requests.
- **Work moved to the Foreman and Drivers [E]: $20–40 in the window, $18–37/wk.**
  - Merge landings (48 user "merged" episodes): one Foreman wake each, half of them cold.
  - Background CI and bisect (54 episodes).
  - Main-as-orchestrator episodes now run under a Driver (about $0.04–0.05 per Foreman or Driver
    turn after the levers).
  - 20–40 Foreman restarts from state.
  - The Foreman reads relayed notes at its next wake.

## 9. Combined result (item 8)

### 9.1 Levers in sequence, all orchestration agents, window $ [S]

| Step (cumulative) | Conservative case | Δ | Optimistic case | Δ |
| --- | --- | --- | --- | --- |
| Simulated baseline (billed $233.59) | 236.37 | | 236.37 | |
| L2 waits outside the LLM (low: polls and sleeps; high: + idle ticks and CI checks) | 230.81 | −5.6 | 225.03 | −11.3 |
| L3 `crf` collapses mechanical runs (low: git/gh and status writes, runs of 3+; high: all classes, runs of 2+) | 222.21 | −8.6 | 148.09 | −76.9 |
| L4a/b hand-back cap (600 / 300 tokens), `crf status` cap (800 / 400 tokens) | 209.24 | −13.0 | 133.36 | −14.7 |
| L4c rotation (150k / 100k) | 165.24 | −44.0 | 114.14 | −19.2 |
| L5 1-h TTL for these roles (optimistic case: + re-arm at 59.5 min) | **126.05** | −39.2 | **76.42** | −37.7 |
| L6 (optional) Sonnet for every Foreman and Driver | 116.84 | −9.2 | 71.26 | −5.2 |

### 9.2 Per role and total, per week

| Role | Today /wk [M] | Design 2 /wk [S] | Saving /wk |
| --- | --- | --- | --- |
| Foreman | $106.8 | $45.6 – $25.9 | **$61–81** |
| Driver (CR) | $77.5 | $49.1 – $32.9 | $28–45 |
| Stack driver | $21.5 | $13.0 – $4.7 | $8–17 |
| Task driver | $7.8 | $6.7 – $5.9 | $1–2 |
| Integrator | $1.4 | $1.5 – $0.8 | −$0.1 to +$0.5 |
| **Orchestration roles, gross** | **$214.9** | **$116.0 – $70.3** | **$99–145** |
| Work moved from the main session [E] | | +$18–37 | −$18–37 |
| Main session `dd375646` | $182.9 | $112.7 – $77.8 | **$70–105** |
| **Total net, this scope** | **$397.8** | | **$132–231 (33–58 %)** |
| Share of the whole measured week ($1,581/wk [M]) | | | **8–15 %** |
| Optional Sonnet for every Foreman and Driver | | | +$5–9 |

The conservative total pairs the conservative levers with the high end of the moved-work cost; the
optimistic total pairs the optimistic levers with the low end.

Factory scope only (runs 1–5 plus the earlier CR batches; real $160.6, $147.7/wk) [S]: design 2
costs $97.5 / $65.8 in the window, a saving of **$58–87/wk** before moved work. For runs 1–5
alone: $66.8 → $48.6 / $31.6.

### 9.3 Per CR, runs 1–3 [M → S]

Scope: the run's subtree plus the main session's orchestration turns in the run window. Coders and
reviewers are unchanged. Main-session orchestration is reduced by the simulated ratio (50 % / 95 %).

| Run | CRs | All-in $/CR today [M] | Orchestration own cost: today → design 2 | Main orchestration in window: today → design 2 | All-in $/CR design 2 | Cut |
| --- | --- | --- | --- | --- | --- | --- |
| 1 (107–124) | 17 | $6.93 | $35.25 → $22.92–11.44 | $7.04 → $3.51–0.35 | **$6.00–5.14** | 13–26 % |
| 2 (125–131) | 7 | $4.86 | $7.57 → $6.19–3.41 | $0.61 → $0.30–0.03 | **$4.62–4.19** | 5–14 % |
| 3 (132–134) | 3 | $3.72 | $5.11 → $4.05–2.07 | $1.05 → $0.52–0.05 | **$3.19–2.37** | 14–36 % |

Run 2 shows the floor: its orchestration was already lean, and coders dominate (CR 131 alone cost
$12.39).

## 10. Implications for design 2

1. **Spend first on context size at the wake, then on the cache policy.**
   - The bill is "wakes × context". Wakes come mostly after a child returns (9–17 min gaps).
   - Rotation or compaction at about 100k, plus hand-back schemas of about 300 tokens, plus a
     1-h TTL or a `crf wait --max <TTL−30s>` re-arm, give most of the saving.
2. **"Waits outside the LLM" must keep the cache warm.**
   - A pure event wait under a 5-min TTL turns cheap polls into rebuilds. Measured result:
     −$2.7 to +$3.4.
   - `crf wait` should exit on an event, on a mailbox note, or at the re-arm deadline.
3. **`crf` should own the multi-step mechanics.**
   - The biggest targets are ship (commit, push, PR), set/render and status. Stack drivers and
     large Foremen gain the most.
   - Each call replaces 3.5–7.5 turns.
4. **The Chief of Staff gain needs the Foreman to be reliable.**
   - It needs a heartbeat, restart from state, mailbox delivery, merge events and digest-only
     notifications. Without them, causes A, C, D and E come back to the main session.
5. **The model switch is a minor lever.** Sonnet is already the default and adds $5–9/wk. Haiku
   would be large but unproven, and it needs contexts under 200k.

## 11. Caveats

- Turn classes and causes come from regular expressions, as in design 1. The ranges cover that
  uncertainty, and the optimistic L3 case is an upper bound.
- The simulator keeps every turn's output and every child's real duration. It does not model:
  - extra turns that a smaller context might cause (re-reading after rotation is modelled
    as 3 turns);
  - latency;
  - rate limits.
- Keep-warm ticks are modelled at 250 tokens of context growth, 100 output tokens and one warm
  read each. Their usage-limit cost is not modelled.
- Main-session savings are scaled by 0.958 (simulated baseline +4 % against billed). The
  orchestration roles need no scaling (within 3 %).
- Run 4/5 was unfinished at the snapshot. Run 3 uses design-1's split of `a21e1ec0a8fc37d31` at
  2026-10-27T16:32:09Z.

## 12. Evidence index

- **Transcripts.** Main session `dd375646-4450-4e52-a643-89ff1d9e405a` and its sub-agents, under
  `~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/`.
- **Run roots:**
  - run 1: `a7dc8322f1d2b1eb9`, `afeef650ccb1e205e`;
  - run 2: `a71ba715a962d0a53`;
  - run 3 (then run 4 start): `a21e1ec0a8fc37d31`;
  - run 4/5: `a725410a2169211f8`.
- **Stack drivers:** `a05ca1697b4543086`, `aafaf178c6de525e2`, `ab5a555448b9c2050`,
  `af782c5d214b2ca48`.
- **Largest contexts:** `aa284441fb21ed442`, `a14fa7d64e7b029f2`, `a35435560038683fc`.
- **Scripts:** `research2/scripts/A1/`.
  - Data: `../data/agents.jsonl`, regenerated with the copied `extract.py`.
  - Outputs: `out/a1_anatomy.txt`, `a1_calib.txt`, `a1_spawnprompts.txt`, `a1_levers.txt`,
    `a2_waits.txt`, `a3_mech.txt`, `a4_small.txt`, `a5_ttl.txt`, `a7_main.txt`,
    `a7_keepwarm.txt`, `a8_combine.txt`.
- **Design-1 inputs reused:**
  - `01-costs.md`: §1 method and prices, §5.3 TTL, §5.4 main session;
  - `02-dynamics.md`: message delivery;
  - `03-judgment.md`: decisions at risk;
  - `04-mechanisms.md`: C7 TTL setting, C26 background notifications.
