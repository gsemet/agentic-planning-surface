# Cost check of the change-request factory sketch, on measured transcripts

- **Date:** 2026-10-27, data snapshot at 2026-10-27T21:48Z (run 4/5 still running).
- **Question:** does the design sketch's saving (`03-design-sketch.md` §12: net **$140–300 a week,
  10–22 %**) hold on real transcripts, and where does it need refining?
- **Verdict:** the **net estimate is CONFIRMED (12–23 % measured vs 10–22 %)**, but its
  **composition is ADJUSTED**. Lever 3 (summarised output, fresh coder) is overstated. Lever 4
  (main session) is understated, because the sketch ignored the main session's own
  orchestration work. Per CR, the cut is smaller than the sketch says (18–39 %, not 35–43 %).

Labels: **[M]** measured from transcripts, **[E]** estimated (method stated next to it).

## 1. Method

- **Sources [M].** Every `~/.claude/projects/**/*.jsonl`, main sessions and sub-agents, with the
  `.meta.json` files for description, model, `parentAgentId` and `spawnDepth`.
  - Excluded: the current design session `c985a2ca-688a-42f5-b17e-bee5b5729ff4` and its sub-agents.
  - 947 agents had at least one assistant message in the window: 13 main sessions and 934
    sub-agents.
- **Window.** 2026-10-17T00:00Z to 2026-10-28T00:00Z. The transcript timestamps are **UTC**
  (`Z` suffix). The machine runs on CET (UTC+1 since 2026-10-25).
  - There is no activity before 2026-10-20T07:33Z. The window therefore holds **7.6 active days**,
    from 2026-10-20T07:34Z to 2026-10-27T21:48Z.
  - "Per week" figures are window figures × 7/7.6 (0.92).
- **Counting and pricing.** The rules and prices are the same as in the Studio cost report
  (`rapport-cout-orchestration.en.md`, Method).
  - Assistant messages are deduplicated by `message.id`.
  - Per message, we keep `input`, `cache_read`, `cache_creation.ephemeral_5m/1h` and `output`.
  - `<synthetic>` messages are excluded.
  - Prices in $/MTok (input, 5-min write, 1-h write, cache read, output): Opus 4/5/8/0.20/20,
    Sonnet 2/2.5/4/0.20/10, Haiku 0.10/0.125/0.20/0.01/0.50, Fable 10/12.5/20/0.25/50.
- **Cache rebuild.** Not the first turn, context above 20k, and writes above 60 % of the context
  (same rule as the report).
  - "Excess" is the rebuild's write cost minus what a warm cache read of the same tokens would
    have cost. It is the amount a removed wait actually saves.
- **New in this analysis.**
  - Per-turn rows: trigger, tools and result sizes.
  - Trigger of each turn: a tool result, a sub-agent hand-back, a task notification, a peer
    message, or a **steering message**. A steering message is a raw `queued_command` from the main
    session or the user.
  - Measured wall time of every foreground Bash call.
  - Error flags in tool results: conflict, failed, denied.
- **Cross-check.** Recomputing the old report's window (10-19 to 10-26) gives $1,486, against the
  report's $1,374. The difference is the end of 10-26: the report was written during that day,
  which cost $162 in total.
- **Roles.** Assigned from descriptions (`scripts/common.py`, `role()`): orchestrator, driver,
  stack driver, task driver, integrator, coder/writer, reviewer, analyst, main, other. Only one
  agent ($4.2) remained in "other".
- **Runs.** Assigned by ancestry from the run roots:
  - run 1: `a7dc8322f1d2b1eb9` ("P1 stack orchestrator", CRs 107–124) and `afeef650ccb1e205e`
    ("Driver CR 123 round 6");
  - run 2: `a71ba715a962d0a53`;
  - run 3: `a21e1ec0a8fc37d31`, split at 2026-10-27T16:32:09Z, its first CR 135 spawn, so the
    rest of that agent counts for run 4/5;
  - run 4/5: `a725410a2169211f8`.
- **Scripts.** All in [scripts/](scripts/).
  - `extract.py`, adapted from `analyze.py`; the originals were copied, not modified.
  - `common.py`, `a_totals.py`, `b_runs.py`, `c_lever1.py`, `d_lever2.py`, `e_lever3.py`,
    `f_lever4.py`, `g_ttl.py`, `h_added.py`, `i_percr.py`.
  - Raw outputs: `out_*.txt` next to this report. PR sizes: `data/prs.json`, from a read-only
    `gh pr list`.
- **Limits.**
  - Role and turn classes come from regular expressions, so they are heuristic.
  - The tool-result reread model explains about 40 % of measured sub-agent cache reads; the rest is
    the base prompt and generated text, as in the old report. Lever 3 figures are therefore ±20 %.
  - Run 4/5 is unfinished.

## 2. Totals for the window (7.6 days) [M]

**$1,705.5 · 947 agents · 32,846 turns · ≈ $1,573 a week.** Models: Sonnet $992, Opus $705,
Fable $8, Haiku $0.1.

| Billing category | Cost | Share |
| --- | --- | --- |
| Cache reads | $827.8 | 48.5 % |
| 5-min cache writes | $488.4 | 28.6 % |
| Output | $276.9 | 16.2 % |
| 1-h cache writes (main sessions) | $112.2 | 6.6 % |
| Uncached input | $0.2 | 0.0 % |

| Role | Agents | Turns | Cost | Share | Cache read | 5-min write | 1-h write | Output |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Coder / writer | 380 | 16,785 | $777.6 | 45.6 % | $411.1 | $231.8 | – | $134.6 |
| Main session | 13 | 3,298 | $278.4 | 16.3 % | $117.8 | – | $112.2 | $48.4 |
| Reviewer | 351 | 5,753 | $222.7 | 13.1 % | $107.1 | $76.2 | – | $39.3 |
| Analyst | 46 | 2,778 | $191.3 | 11.2 % | $107.0 | $52.6 | – | $31.7 |
| Orchestrator | 31 | 1,184 | $115.2 | 6.8 % | $39.7 | $65.9 | – | $9.6 |
| Driver (per CR) | 92 | 2,011 | $83.8 | 4.9 % | $23.5 | $51.2 | – | $9.1 |
| Stack driver | 5 | 620 | $23.3 | 1.4 % | $16.6 | $4.6 | – | $2.1 |
| Task driver (CR 135) | 24 | 257 | $7.8 | 0.5 % | $2.1 | $4.5 | – | $1.1 |
| Integrator (CR 135) | 4 | 72 | $1.2 | 0.1 % | $0.6 | $0.4 | – | $0.2 |
| Other | 1 | 88 | $4.2 | 0.2 % | $2.3 | $1.3 | – | $0.6 |

| Workstream | Agents | Cost | Share |
| --- | --- | --- | --- |
| Requirements base (CRs 059/060) | 272 | $497.4 | 29.2 % |
| CR pipeline before run 1: orchestrated batches 10-22 to 10-26, CRs 023–106 | 277 | $384.7 | 22.6 % |
| Main session (white-paper project) | 6 | $235.6 | 13.8 % |
| CR 056 refactor | 28 | $153.1 | 9.0 % |
| **CR factory run 1** (CRs 107–124) | 100 | $110.8 | 6.5 % |
| Deep-UX fix plan (T#/P# tasks) | 62 | $99.2 | 5.8 % |
| **CR factory run 4/5** (CR 135 and CRs 137–143 so far) | 120 | $92.0 | 5.4 % |
| Other projects (main sessions) | 7 | $42.8 | 2.5 % |
| **CR factory run 2** (CRs 125–131) | 30 | $33.4 | 2.0 % |
| One-off tasks | 22 | $26.2 | 1.5 % |
| Audit research (input to CR 135) | 6 | $17.8 | 1.0 % |
| **CR factory run 3** (CRs 132–134) | 17 | $12.5 | 0.7 % |

The **factory scope** is runs 1–5 plus the earlier orchestrated CR batches: **$633.5 (37 %)**
[M], plus about $85 of main-session orchestration (§5.4), so about **42 %** of the window.

## 3. CR factory runs 2–5 (and run 1 for reference)

### 3.1 Per run [M]

Orchestration own cost is the own cost of orchestrators, drivers, stack drivers, task drivers and
integrators. Overhead is that cost divided by the subtree cost.

| Run | CRs | Window (UTC) | Subtree cost | Orchestration own cost | Overhead | $/CR, subtree | Coder + reviewer $/CR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 (107–124) | 17 | 10-26 18:04 → 10-27 11:16 | $110.79 | $35.25 (stack driver $16.90) | **32 %** | $6.52 | $4.44 |
| 2 (125–131) | 7 | 10-27 10:41 → 13:08 | $33.44 | $7.57 | **23 %** | $4.78 | $3.70 |
| 3 (132–134) | 3 | 10-27 15:14 → 18:05 | $10.10 | $5.11 (Opus orchestrator) | **51 %** | $3.37 | $1.66 |
| 4/5 (135, 137–143, running) | 7 so far | 10-27 15:14 → 21:43 | $94.44 | $15.62 | **17 %** | $13.49 (CR 135: $63.88 for 19/26 tasks) | $11.26 |

All-in figures, adding the main session's orchestration turns during each run window, and the
sketch's estimate per CR [E]:

| Run | Main session in the run window (orchestration turns) | All-in $/CR today [M] | Sketch $/CR [E] | Cut [E] |
| --- | --- | --- | --- | --- |
| 1 | $16.11 ($7.04) | $6.93 | $4.99 | 28 % |
| 2 | $3.51 ($0.61) | $4.86 | $4.01 | 18 % |
| 3 | $3.29 ($1.05) | $3.72 | $2.27 | 39 % |
| 4/5 (partial) | $5.34 ($1.15) | $13.65 | $11.48 | 16 % |

The sketch estimate assumes:

- 85 % of the orchestration own cost and 70 % of the main session's orchestration turns removed;
- coder and reviewer rebuild excess after long suites and CI removed;
- 8 runner agents per CR at $0.01, plus 0.3 extra rounds per CR at $0.55.

Run windows 3 and 4/5 overlap, so their main-session figures share some turns. Script:
`scripts/i_percr.py`.

### 3.2 Per CR [M]

Cost of the CR's own subtree: driver, coders and reviewers. Lines are the merged PR's additions plus
deletions.

- **Run 1:**

  | CR | Cost | Lines | Per 100 lines |
  | --- | --- | --- | --- |
  | 107 | $2.13 | 68 | $3.14 |
  | 108 | $0.97 | 51 | – |
  | 109 | $5.00 | 210 | – |
  | 110 | $5.85 | 552 | – |
  | 111 | $2.15 | 311 | – |
  | 112 | $4.78 | 255 | – |
  | 113 | $3.60 | 290 | – |
  | 114 | $4.35 | 731 | – |
  | 115 | $15.76 | 1,796 | $0.88 (4 rounds) |
  | 116 | $2.93 | 283 | – |
  | 117 | $2.53 | 139 | – |
  | 118 | $2.18 | 140 | – |
  | 119 | $4.64 | 830 | – |
  | 120 | $2.34 | 344 | – |
  | 121 | $2.02 | – | dropped |
  | 123 | $21.01 | 1,342 | 6 rounds |
  | 124 | $1.65 | 121 | – |

- **Run 2:**

  | CR | Cost | Lines | Per 100 lines |
  | --- | --- | --- | --- |
  | 125 | $1.66 | 283 | – |
  | 126 | $2.41 | 160 | – |
  | 127 | $1.18 | 60 | – |
  | 128 | $2.30 | 376 | – |
  | 129 | $3.87 | 296 | – |
  | 130 | $4.93 | 312 | 3 rounds |
  | 131 | $12.39 | 2,105 | $0.59 |

- **Run 3:**

  | CR | Cost | Lines | Rounds |
  | --- | --- | --- | --- |
  | 132 | $1.36 | 144 | – |
  | 133 | $1.92 | 378 | 2 |
  | 134 | $2.60 | 198 | – |

- **Run 4/5, unfinished:**

  | CR | Cost so far | Notes |
  | --- | --- | --- |
  | 135 | $63.88 | 101 agents; coders $41.4, reviewers $13.5, task drivers $7.77, integrators $1.21 |
  | 137 | $1.22 | – |
  | 138 | $3.78 | – |
  | 139 | $3.97 | – |
  | 140 | $2.26 | – |
  | 141 | $5.07 | – |
  | 143 | $9.76 | – |

- **The orchestrated batches before run 1 [M]:** $384.7, of which $94.7 (25 %) is orchestration
  own cost.
  - "Orchestrator P1+P2 stacked PRs" (`aa284441fb21ed442`): 32 %.
  - "Orchestrator night run" (`a4ac0655afa7e1c8d`): 26 % once its 12 drivers are counted. Its own
    cost is $0.76.
- **Rounds per CR, factory scope [M]:** mean 1.40, median 1. 21 % of CRs needed more than one
  round; 9 % needed 3 or more.

## 4. Lever 1: orchestrators and drivers become code

### 4.1 Base [M]

| Scope | Roles | Agents | Turns | Own cost | Rebuilds | Rebuild excess |
| --- | --- | --- | --- | --- | --- | --- |
| Runs 1–5 | orch 4, drivers 43, stack 4, task 24, integrators 4 | 79 | 1,559 | $63.54 | 95 | $18.0 |
| Earlier CR batches | orch 18, drivers 47, stack 1 | 66 | 1,878 | $94.71 | 118 | $39.3 |
| Other workstreams (requirements orchestrators K/L/F…, CR 056 driver) | orch 9, drivers 2 | 11 | 707 | $73.00 | 58 | $34.1 |
| **Total** | | **156** | **4,144** | **$231.3** (≈ $213 a week) | **271** | **$91.4 (40 % of own cost)** |

The rebuild gaps are mostly 5–60 minutes, the time of CI or of a sub-agent:

- orchestrators: 58 rebuilds at 5–15 min, 42 at 15–60 min, 14 above 1 h;
- drivers: 82 at 5–15 min, 45 at 15–60 min, 6 above 1 h.

Most expensive orchestration agents [M]:

| Agent | Description | Own cost | Turns | Mean context | Rebuilds | Bash calls |
| --- | --- | --- | --- | --- | --- | --- |
| `aa284441fb21ed442` | P1+P2 orchestrator | $40.03 | 285 | 263k | 36 ($24.65) | 208 |
| `a14fa7d64e7b029f2` | Orchestrator L | $25.11 | 230 | 303k | – | – |
| `a3a9ea083fe2f3289` | Driver CR 056 | $20.39 | 96 | – | 24 ($16.27) | – |
| `a05ca1697b4543086` | Stack driver 107–120 (run 1) | $16.90 | 324 | 190k | – | 311 |

### 4.2 What their turns do [M]

All 4,144 turns, classified by trigger, then by tools (`scripts/c_lever1.py`):

| Turn class | Turns | Cost | Share | In the sketch |
| --- | --- | --- | --- | --- |
| Mechanical: reads and other shell | 975 | $37.74 | 16.3 % | `crf status` / `render` |
| Hand-back handling (reads a child's report) | 273 | $35.37 | 15.3 % | schema verdict, script |
| Hand-back, then spawn the next agent | 190 | $29.04 | 12.6 % | script |
| Mechanical: git / gh | 447 | $21.54 | 9.3 % | `crf ship` / `stack` |
| Mechanical: poll / wait / CI | 499 | $19.19 | 8.3 % | `crf ci wait` |
| Mechanical: status or table write | 355 | $14.66 | 6.3 % | `crf set` / `render` |
| Spawn | 281 | $12.53 | 5.4 % | script |
| First turn (reads the brief) | 156 | $11.09 | 4.8 % | gone |
| Mechanical: gates | 260 | $9.07 | 3.9 % | `crf gate` |
| Background wait resumed | 95 | $6.52 | 2.8 % | gone |
| Send message / final report | 53 | $2.61 | 1.1 % | events, `crf land` |
| **Exception** (tool error, conflict, denial, failed gate or CI) | 318 | $10.85 | 4.7 % | **judgment**: conflict fixer, or a `blocked` CR for the main session |
| **Steering** (message from the main session or the user) | 46 | $10.45 | 4.5 % | **judgment**: `crf note`, main session |
| Edits to source or other files | 171 | $5.78 | 2.5 % | **judgment**: coder or conflict fixer |
| Peer message from another agent | 25 | $4.82 | 2.1 % | **judgment** |

- **Mechanical or scripted turns:** $199.4 (86.2 %). **Judgment turns** that must survive somewhere:
  **$31.9 (13.8 %)**.
- Hand-back handling sometimes carries real judgment, for example reading a FIX-REQUIRED review or
  a blocked report. The low end of the range therefore assumes **75 %** removable.
- **Tool calls in runs 1–5 [M], 1,750 calls:**
  - shell reads 335, spawns 268, other shell 213, shell writes 206;
  - long suites 121: drivers run gates themselves;
  - git writes 106, git reads 101, hand-backs 90, polls 69, okfreq 41, gh 51, `SendMessage` 14;
  - fast gates 15.
  - About 95 % are mechanical.
- **Steering, counted [M]:**
  - 72 incoming messages from the main session or the user to orchestration agents in 7.6 days:
    60 to orchestrators, 12 to drivers. 46 turns are directly triggered by them.
  - Direct cost **$10.45**; the episode with follow-up tool turns costs **$19.9**.
  - Within runs 1–5: 12 messages, 8 turns, $2.13 direct and $3.30 for the episode.
  - Coders received 9 such messages ($0.98).
  - Steering is cheap; its value lies elsewhere. A channel such as `crf note` must keep it.

### 4.3 Saving [E]

75–86 % of $213 a week gives **$160–184 a week**. The sketch said $140–165. The sketch's base was
orchestrators plus drivers only ($167). The measured base also includes stack drivers, task drivers
and integrators.

## 5. Levers 2 to 4

### 5.1 Lever 2: no LLM waits [M]

Rebuilds per role, with the gap before them. Excess is the rebuild write minus a warm read.

| Role | Rebuilds | Write $ | Excess $ | Under 5 min | 5–15 min | 15–60 min | Over 1 h |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Coder / writer | 179 | $93.0 | $87.1 | 7 | **151 ($75.3)** | 15 | 6 |
| Main session | 42 | $63.9 | $62.3 | 1 | 1 | 0 | **40 ($58.0)** |
| Orchestrator | 114 | $57.5 | $53.1 | 0 | 58 | 42 | 14 |
| Driver | 133 | $35.7 | $33.9 | 0 | 82 | 45 | 6 |
| Analyst | 22 | $21.1 | $19.7 | 0 | 8 | 9 | 5 |
| Reviewer | 29 | $8.9 | $8.2 | 0 | 21 | 7 | 1 |
| Stack driver, task driver | 24 | $4.8 | $4.4 | – | – | – | – |

**What coders waited for before a rebuild [M]** (the tool call of the previous turn,
`d_lever2.py`):

| Waited for | Rebuilds | Excess | Removable by `crf`? |
| --- | --- | --- | --- |
| Long suite: `just visual`, `ci-visual`, integration, window tests, `gate.sh` | 75 | **$41.75** | yes |
| Resumed after its own hand-back (agent kept alive for the next round) | 34 | $14.38 | fresh coder instead (see 5.2) |
| CI watch or poll loop (`gh run`, `until … sleep`, `wait.sh`) | 16 | **$9.94** | yes |
| Background task notification (a long suite started in the background) | 13 | **$5.49** | yes |
| Fast gates (`just check`, unit tests) | 6 | $3.50 | no: the coder keeps them |
| Other shell, writes, reads, compaction | 35 | $12.0 | no |

- **Reviewers:** long suites $2.58 removable, kept-alive $5.12.
- **Analysts:** kept-alive $14.06; long suites $1.68 removable.
- **Measured durations of foreground Bash calls in coders and reviewers:**
  - long suites: p50 39 s, p90 337 s; 48 of 210 last more than 5 minutes;
  - polls: p50 115 s, p90 407 s;
  - fast gates: p50 16 s, p90 42 s.
- **Removable base:** $57.2 for coders, $3.0 for reviewers, $1.7 for analysts, so **$61.9 in the
  window, $57 a week**.
  - Factory scope alone: $31.9.
  - Not every real-window run can leave the coder: a UI fix must reproduce the bug. The range is
    therefore 70–100 %, **$40–57 a week [E]**.
  - **CONFIRMED** against the sketch's $35–65.

### 5.2 Lever 3: shorter coder contexts

**Tool-result cost [M, modelled].** Each result is written once, then reread on every later turn
(`e_lever3.py`).

| Coder result type | Calls | Average tokens | Average turns carried | Cost | Factory scope |
| --- | --- | --- | --- | --- | --- |
| Shell read (`cat`, `sed`, `grep`, `ls`) | 8,525 | 1,367 | 49 | **$163.3** | $90.6 |
| Other shell | 2,404 | 852 | 29 | $17.1 | $5.7 |
| Read tool | 175 | 3,856 | 42 | $11.7 | $0.6 |
| Shell writes and edits | 3,181 | 322 | 37 | $11.5 | $5.8 |
| git | 652 | 1,023 | 37 | $8.3 | $6.5 |
| Images | 342 | 1,600 | 33 | $5.2 | $4.7 |
| **Fast-gate output** | 431 | **446** | 23 | **$1.6** | $1.2 |
| **Long-suite output** | 243 | **401** | 24 | **$1.0** | $0.4 |
| **gh / CI output** | 167 | 444 | 36 | **$1.0** | $0.8 |

- **Outputs are already short.** Coders already `tail` and `grep` their test and CI output: 400 to
  450 tokens on average.
  - Capping every non-read output above 1,000 tokens (about 30 lines) saves **$16.9 for coders,
    $10.6 for reviewers and $5.6 for others** in the window.
  - Most of that is git diffs and ad hoc shell, which reviewers need. The `crf` summaries
    themselves (gates, CI, gh) save **under $3 a week [E]**.
- **Targeted reads** cap shell reads above 3k tokens. The upper bound is $46 in the window
  (coders $23.5, reviewers $8.9, others $13.7). With 25–50 % realised, that gives **$10–21 a week
  [E]**, at low confidence.
- **Context growth [M]:**
  - coders: median 34k → 109k (3.2×), mean context per turn 127k;
  - reviewers: 1.8×;
  - analysts: 5.7×.
- **Fresh coder per round is already the norm [M].**
  - Only 10 of 116 round-1 coders were resumed after a hand-back.
  - Of the 77 agents resumed after a hand-back ($108.5 spent after the first one), most are
    requirements analysts and writers.
  - Exploration before the first source edit:

    | Round | Coders | Turns before first edit, median | Cost before first edit, median (mean) |
    | --- | --- | --- | --- |
    | 1 | 116 | 17 | $0.44 ($0.68) |
    | 2 | 28 | 8 | $0.25 ($0.42) |
    | 3+ | 16 | 18 | $0.63 ($0.69) |

  - A hand-over note that halves re-exploration on the 55 round-2+ coders saves about
    **$6–15 a week [E]**.
- **Lever 3 total: $15–40 a week [E].** **ADJUSTED down** from $30–80. The $180 of shell reads is
  source code that a coder must read, not command output.

### 5.3 The one-hour TTL decision [M]

| Item | Window cost |
| --- | --- |
| Sub-agent 5-min writes | $488.4 |
| of which cold starts | $53.4 |
| of which incremental writes | $214.0 |
| of which rebuilds | $221.1 ($209.4 with a gap under 1 h, $11.6 over 1 h) |

- **One-hour TTL today:** non-rebuild writes cost +$160.4 at 1.6×. Rebuilds under 1 h become reads,
  saving $195.5. Rebuilds over 1 h cost +$7.0. **Net: $28 cheaper in the window.** Factory
  sub-agents alone: $23 cheaper.
- **After levers 1 and 2** (orchestration roles gone, waits after long suites and CI gone):
  +$145.0 extra against $50.6 saved, so **+$94 more expensive in the window (≈ +$87 a week)**.
- **Verdict:** the rejection is **CONFIRMED**, but the sketch's "+$128 a week" ignored the rebuilds
  that the TTL removes. The real penalty is about +$87 a week once levers 1 and 2 are in place.
- Before those levers exist, a one-hour TTL alone would be a cheap stop-gap. It saves about
  $28 per 7.6 days.

### 5.4 Lever 4: bounded main session [M]

- **Main session `dd375646-4450-4e52-a643-89ff1d9e405a`:**
  - 2,383 turns, **$198.10**, Opus with the one-hour cache, 10-20 → 10-27;
  - context: median 183k, mean 191k, p90 321k, maximum 501k;
  - **17 compactions**: context before them median 355k, after them median 55k.
- **Cost by context band:**

  | Context | Turns | Cost |
  | --- | --- | --- |
  | Under 50k | 13 | $1.1 |
  | 50–100k | 427 | $21.5 |
  | 100–150k | 443 | $22.1 |
  | 150–200k | 450 | $40.3 |
  | 200–300k | 713 | $65.9 |
  | Over 300k | 337 | $47.1 |

- **Cost components:** reads $89.2, 1-h writes $77.4, output $31.5.
- **Rebuilds:** 42 for $62.3 of excess. 40 of them come after more than 1 h of user absence.
- **Who it works for [M]** (turn class from trigger and tools, `f_lever4.py`):

  | Turn class | Turns | Cost | Share |
  | --- | --- | --- | --- |
  | User message, first turn of the reply | 328 | $50.29 | 25.4 % |
  | Text-only reply | 395 | $23.72 | 12.0 % |
  | **Orchestration: read or write run state** (`STATE`, `ORCHESTRATOR`, `03-requests`, worktrees) | 341 | $22.46 | 11.3 % |
  | **Orchestration: react to an agent or task notification** | 211 | $19.45 | 9.8 % |
  | **Orchestration: git / gh status** | 151 | $13.52 | 6.8 % |
  | **Orchestration: (re)start agents** (40 orchestrator spawns in total, 7 restarts or resumes) | 84 | $9.51 | 4.8 % |
  | **Orchestration: relay or steer an agent** (207 `SendMessage` calls) | 122 | $9.23 | 4.7 % |
  | **Orchestration: ad hoc scripts** | 87 | $7.22 | 3.6 % |
  | **Orchestration: monitoring** (`ListAgents`, waits) | 55 | $3.29 | 1.7 % |
  | Research and reading, backlog, other | 609 | $39.4 | 19.9 % |

- **Orchestration:** **$84.68 (43 %)**. **Conversation:** $74.01 (37 %).
- **By episode:**
  - **245 episodes started by a notification: $73.7.** In the sketch these mostly disappear,
    because a workflow notifies at run end only.
  - 190 user-started episodes containing orchestration actions: $98.5. Steering stays here.
  - 138 user-started episodes without orchestration: $25.8.
  - The user sent 403 messages and the session received 375 notifications.
- **Other main sessions in the white-paper project:** `069f6dee…` ($15.83, 12 % orchestration),
  `521459c8…` ($17.91, 20 %) and `230cd2e4…` ($2.99, 24 %).
- **Saving [E]:**
  - (a) Removing 60–80 % of main-session orchestration ($90.8 in the window, $84 a week) gives
    $50–67 a week.
  - (b) A simulated `--autocompact 100000` on the remaining turns: re-summarise at 100k, restart
    at 45k, $0.16 per summary. It cuts `dd375646` by 23 % (71 compactions instead of 17); a cap at
    150k cuts it by 21 %. The range is 10–23 % of the remaining $150–167 a week, so $15–38.
  - **Lever 4: $65–105 a week**, **ADJUSTED up** from $20–40. The sketch counted compaction only,
    not the Chief-of-Staff effect of taking orchestration out of the main session.

## 6. Added costs of the sketch

- **Runner agents [M+E].**
  - Today's drivers make a median of 12 tool calls per CR (9 Bash calls), excluding CR 135. Mean
    per CR: 6.5 shell reads, 2.8 spawns, 2.4 status writes, 2.2 git calls and 0.5 CI polls.
  - In the sketch, that becomes about 6–8 `crf` calls per CR:
    - gate × 1.4 rounds;
    - ship;
    - CI wait;
    - 2–3 sets;
    - a share of the stack.
  - The factory had 104 CRs in 7.6 days, so about 560–750 calls a week.
  - Measured Haiku agents start at a 36k context; a 1–2 turn runner then costs about
    $0.005–0.01, so **$3–8 a week**.
  - **On Sonnet**, agents of 3 turns or fewer measured a median of **$0.088**, which gives
    **$50–66 a week**: a third of lever 1. **A Haiku runner is a hard requirement.**
- **Supervision.** `/loop` ticks on a bounded, warm one-hour cache cost $0.02–0.05 per tick, so
  **$3–10 a week [E]**.
- **Extra rounds [M+E].**
  - In factory coders, 13 (strict) to 67 (broad) long-suite or CI failures were fixed inside the
    same coder (`h_added.py`). They touch up to 35 CRs.
  - "Strict" means a foreground wait over 5 minutes plus a "fail" flag in the output. "Broad"
    adds CI polls and gate-type commands.
  - Exit codes are useless here: coders mask them with `; echo exit $?`.
  - In the sketch, each failure becomes a fresh coder: cold start plus re-exploration,
    $0.42–0.69 measured. That gives **$5–43 a week**. It also pushes more CRs to the three-round
    cap, which 9 % already reach.

## 7. Refined lever table

| Lever | Measured base (window, 7.6 days) | Removable share and evidence | Saving per week | Confidence | Sketch |
| --- | --- | --- | --- | --- | --- |
| 1 Orchestrators and drivers become code | Own cost **$231.3** [M]; 271 rebuilds, $91.4 excess [M] | 75–86 %: 86.2 % of their turn cost is mechanical or scripted, 13.8 % is judgment [M] | **$160–184** | high | $140–165, slightly ADJUSTED up |
| 2 No LLM waits in coders, reviewers and analysts | Removable rebuild excess **$61.9** [M]: long suites $41.8, CI polls $9.9, background waits $5.5 | 70–100 %: some real-window reproduction stays in the coder | **$40–57** | high | $35–65, CONFIRMED |
| 3 Shorter coder contexts | Shell reads $163 (coders) [M, modelled]; command output only $3.6 [M] | `crf` summaries under $3; targeted reads 25–50 % of $46; hand-over note | **$15–40** | low | $30–80, ADJUSTED down |
| 4 Bounded main session | $235.6 for main sessions; orchestration turns **$90.8 (43 % of `dd375646`)** [M] | 60–80 % of orchestration turns; autocompact 10–23 % of the rest [E, simulated] | **$65–105** | medium | $20–40, ADJUSTED up |
| Gross | | | **$280–386** | | $225–350 |
| Overlap | | 3–8 %: the levers apply to disjoint roles, except smaller rebuilds | −$10–30 | | −$25–50 |
| Runners (Haiku) | 6–8 calls per CR × 94 CRs a week | measured Haiku cold start 36k | −$3–8 (Sonnet: −$50–66) | medium | −$4–10 |
| Supervision | – | – | −$3–10 | low | −$3–10 |
| Extra rounds | 13–67 in-coder long or CI failures [M] | × $0.42–0.69 per fresh coder [M] | −$5–43 | medium | −$10–30 |
| **Net** | measured week ≈ **$1,573** | | **$189–365 a week = 12–23 %** | | $140–300 = 10–22 % |

- **Factory scope alone:** runs 1–5, the earlier CR batches, and the main session's orchestration.
  - Gross $193–258 a week; net **about $117–242 a week [E]**.
  - The sketch said $85–180, so this is **ADJUSTED up**. The difference is the main session's
    orchestration work.
- **Per CR, runs 1–3 [M → E]:**
  - today **$3.72–6.93** all-in, not the sketch's $2.2;
  - with the sketch: $2.27–4.99, a **18–39 % cut**, not the sketch's 35–43 %.
  - Run 2 shows the floor. Its orchestration was already lean (23 %), and coders dominate: CR 131
    alone cost $12.39.

**Overall verdict: CONFIRMED on the net share (12–23 % vs 10–22 %), ADJUSTED on composition.**

- Lever 4 carries more of the saving and lever 3 less.
- The per-CR cut is smaller.
- The one-hour-TTL argument holds, but with corrected numbers.
- A Haiku runner is a precondition. On Sonnet runners, the net drops by about $50 a week.

## 8. Surprises

1. **A one-hour TTL would save money today:** −$28 in the window, because sub-agents rebuild
   $221 of cache. It only becomes a loss (+$87 a week) after levers 1 and 2. The sketch's +$128
   ignores the rebuilds it removes.
2. **Command output is already small.**
   - Coder test, CI and gh outputs average 400–450 tokens, because agents `tail` and `grep`.
   - The $163 of coder shell reads is source code. `crf` summaries barely move it.
3. **"Fresh coder per round" is already the practice.** Only 10 of 116 round-1 coders were
   resumed. The hand-over note is the only new part.
4. **The main session is a hidden orchestrator.**
   - 43 % of `dd375646` ($84.7) is orchestration: 245 notification-driven episodes ($73.7),
     207 `SendMessage` calls, 87 ad hoc script turns.
   - The sketch did not count this, and it is where the Chief-of-Staff goal pays.
5. **Stack drivers are expensive.** The run-1 stack driver cost $16.90: 324 turns at a mean
   context of 190k, more than the run-1 orchestrator ($6.97).
6. **Rebuilds are 40 % of the orchestration roles' own cost:** $91.4 of $231.3.
7. **Steering is cheap but frequent.**
   - 72 messages from the main session or the user to orchestration agents, plus 9 to coders.
   - $10.5 direct, about $20 with follow-up turns.
   - A `crf note` channel keeps the same capability for very little.
8. **Exit codes are useless as a signal.** Coders and drivers mask them (`; echo exit $?`): no
   long-suite failure had a non-zero tool exit. `crf` must own exit codes and verdicts.
9. **Per-CR cost is driven by a few CRs:** CR 123 ($21.01, 6 rounds), CR 115 ($15.76, 4 rounds),
   CR 131 ($12.39) and CR 135 ($63.88 so far). Round caps and specification stability matter as
   much as orchestration.
10. **Haiku is almost unused** (2 agents, $0.10). The sketch's runner cost depends on it.

## 9. Evidence index

- **Main sessions:** `dd375646-4450-4e52-a643-89ff1d9e405a`, `069f6dee-582f-476d-a4e9-a9a9707a0100`,
  `521459c8-bb7f-489f-ad0a-3f6e3c36685c` and `230cd2e4-bccf-4c47-a7f3-d3db24c88d12`, under
  `~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/`.
- **Run roots:** `a7dc8322f1d2b1eb9` (run 1), `afeef650ccb1e205e` (CR 123 round 6),
  `a71ba715a962d0a53` (run 2), `a21e1ec0a8fc37d31` (run 3, then run 4 start), `a725410a2169211f8`
  (run 4/5 restart). All under `dd375646-…/subagents/agent-<id>.jsonl`.
- **Stack drivers:** `a05ca1697b4543086` (107–120), `aafaf178c6de525e2` and `ab5a555448b9c2050`
  (run 2), `af782c5d214b2ca48` (132–134).
- **Run state:**
  `/Users/az02065/Projects/DevTools/markdown-okf-schema-studio/.agents/changes/03-requests/`
  (`RUN-BRIEF.md`, `RUN-BRIEF-addendum-run5.md`, `ORCHESTRATOR.md`, `ORCHESTRATOR-STATUS.md`,
  `135-…/STATE.md`). PRs #113–#142 come from `data/prs.json`.
- **Raw outputs:** `out_a.txt` (totals), `out_b.txt` (runs and CRs), `out_c.txt` (lever 1),
  `out_d.txt` (lever 2), `out_e.txt` (lever 3), `out_f.txt` (lever 4), `out_g.txt` (TTL),
  `out_h.txt` (added costs), `out_i.txt` (per-CR what-if).
