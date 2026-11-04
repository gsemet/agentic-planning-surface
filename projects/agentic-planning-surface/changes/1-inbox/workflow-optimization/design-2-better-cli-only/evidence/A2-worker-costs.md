# A2: Worker-role costs and token levers for design 2 (Coder, Inspector, Analyst, Conflict fixer)

- **Date:** 2026-10-27. Data snapshot cut at 2026-10-27T21:48:30Z, the same as design-1 `01-costs.md`.
  It reproduces $1,705.5, 947 agents and 32,846 turns exactly.
- **Scope:** every worker sub-agent in the window, 777 agents, 25,316 turns, **$1,191.6 (70 % of
  the window)**. Session `c985a2ca…` is excluded.
- **Labels:** **[M]** measured, **[S]** simulated turn by turn on the real transcripts,
  **[E]** estimated (method stated next to it). Weekly figure = window × 0.92 (7.6 active days).
- **Prices.** Same table as design-1, checked against the claude-api skill. In $/MTok, the five
  prices are input, 5-min write, 1-h write, cache read and output.
  - Opus 5.5: 4 / 5 / 8 / 0.20 / 20.
  - Sonnet 5.5: 2 / 2.5 / 4 / 0.20 / 10.
  - Haiku 5.5: 0.10 / 0.125 / 0.20 / 0.01 / 0.50, **×5 above 100K-token prompts**. Design-1
    ignored that surcharge.
- **Scripts:** `scripts/A2/`. Design-1 scripts were copied unchanged except for the data path and
  the cut-off. New scripts: `w_extract.py`, `wcommon.py` and `a2_*.py`. Raw outputs are in
  `data/A2/out_*.txt`.

## 0. Role mapping

Design-1 `role()` is used first, then split by workstream (`wcommon.wrole`):

| Design-2 role | Today's agents | Agents | Turns | Cost [M] |
| --- | --- | --- | --- | --- |
| **Coder** | CR coders, fix-plan implementers, CR 056 step coders | 251 | 13,682 | $636.2 |
| **Inspector** | CR, fix-plan and CR 056 reviewers | 236 | 2,674 | $93.9 |
| **Conflict fixer** | "Resolve rebase conflicts", "Review conflict resolution" | 21 | 160 | $3.2 |
| Writer (requirements) | SwRS/XC writers, gap closers, shrink audit | 117 | 2,998 | $139.5 |
| Critic (requirements) | critics, re-checks, review batches | 106 | 3,024 | $127.5 |
| Analyst (requirements) | analysts, inventories, locators | 39 | 2,538 | $174.2 |
| Analyst (other) | audits, feasibility | 7 | 240 | $17.1 |

Factory scope (runs 1–5 plus the CR batches before run 1): coders $419.3, inspectors $52.1 and
conflict fixers $3.2 [M].

## 1. Anatomy [M]

| Role | Cost | Cache read | 5-min write | Output | Model (agents) | Turns/agent p50 | Ctx/turn p50 / p90 | First ctx p50 | Last ctx p50 | Output tok/turn mean / p50 / p90 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Coder | $636.2 | $344.1 | $189.9 | $102.1 (16 %) | Sonnet 204, Opus 47 (Opus = 44 % of $) | 43 | 112k / 242k | 34k | 117k | 508 / 252 / 1,233 |
| Inspector | $93.9 | $33.5 | $43.4 | $17.0 (18 %) | Sonnet 182, Opus 54 (49 % of $) | 8 | 56k / 115k | 34k | 56k | 419 / 271 / 923 |
| Conflict fixer | $3.2 | $1.2 | $1.7 | $0.2 | Sonnet 19, Opus 2 | 6 | 41k / 54k | 33k | 41k | 81 / 16 / 284 |
| Writer (req) | $139.5 | $66.1 | $40.9 | $32.4 (23 %) | Sonnet 116, Opus 1 | 19 | 93k / 234k | 34k | 103k | 1,010 / 426 / 2,559 |
| Critic (req) | $127.5 | $73.2 | $32.2 | $22.2 (17 %) | Sonnet 106 | 20 | 101k / 245k | 34k | 107k | 733 / 425 / 1,342 |
| Analyst (req) | $174.2 | $102.4 | $45.6 | $26.2 (15 %) | Sonnet 34, Opus 3, Haiku 2 | 54 | 179k / 412k | 34k | 227k | 1,027 / 362 / 1,917 |

- **Thinking share of output [E]:** output tokens minus visible text and tool input (chars/3.5).
  - Coder 41 %, Inspector 45 %, Writer 53 %, Critic 62 %, Analyst 55 %.
  - Thinking costs about **6–11 % of each role's cost**: coder $59.8, writer $17.4,
    inspector $10.3, critic $14.2, analyst $14.7.
  - Thinking text is empty in the transcripts (redacted), so this is a residual.

### 1.1 What the first turn is made of [M]

Chars/token is calibrated at **3.81** on 777 first turns (p10–p90 spread ±1 %). Each first turn
contains the following (medians, tokens):

| Part | Tokens | Note |
| --- | --- | --- |
| **Tool schemas** | **21.6–23.0k** | `Artifact` alone **15.5k**; `Agent` 1.4k, `Bash` 1.2k, `Skill` 0.9k, `ReportFindings` 0.8k, `Read` 0.75k, `ToolSearch` 0.7k, `ListAgents` 0.5k |
| **Skill listing** | **5.1k** | 32 skills listed to every worker |
| Instruction files | 3.9k | **the white-paper `AGENTS.md`** (9.8k chars) + `MEMORY.md` + RTK. All 777 workers get it, but they work in the Studio repo |
| Deferred tools, MCP, environment | 1.6k | |
| System prompt | 0.7k | |
| **Brief from the driver** | **0.2–0.5k** (p90 0.5–1.2k) | the actual role card today |
| **Total** | **≈ 34k** | ~18k read from a shared cache, ~15k written |

- **All 934 sub-agents are `general-purpose`** [M]. No transcript shows a restricted tool set, so
  the size of a slimmer prefix is [E] until one test run shows it.
- **Instructions read by tool [M]:**
  - 145 of 251 coders read project rules (`AGENTS.md`, `constitution.md`, `README.md`,
    `CONTRIBUTING.md`, guidelines), **3.3k tokens per reader**. The largest are `constitution.md`
    (104k tokens over all coders), `README.md` (103k) and `AGENTS.md` (98k).
  - Inspectors: 41 of 236 read them (2.7k each).
  - Mean role-card payload (brief + rules read): coder 2.5k, inspector 0.9k, writer 3.2k,
    analyst 3.3k.

### 1.2 Simulated: shorter role cards versus a slimmer harness prefix [S]

The cut tokens are removed at their real position. Every later turn is billed at read or write
price according to that turn's cache split (`a2_cards.py`). Window $:

| Role | Card −30 % | Card −50 % | Drop `Artifact` schema | Drop `Agent`/`ListAgents`/`ReportFindings` | Drop skill listing | Drop wrong `AGENTS.md` + `MEMORY` | **All prefix cuts** (% of role) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Coder | $3.0 | $5.1 | $50.3 | $5.1 | $16.8 | $9.9 | **$86.4 (13.6 %)** |
| Inspector | $0.3 | $0.6 | $9.4 | $1.0 | $3.2 | $1.9 | **$19.9 (21 %)** |
| Writer | $0.8 | $1.3 | $10.7 | $1.8 | $3.5 | $2.1 | $19.8 (14 %) |
| Critic | $0.3 | $0.4 | $10.3 | $1.8 | $3.4 | $2.0 | $18.8 (15 %) |
| Analyst (req) | $0.8 | $1.4 | $8.9 | $1.5 | $2.9 | $1.8 | $15.5 (9 %) |
| **All workers** | **$5.4** | **$9.0** | $91.6 | $11.5 | $30.4 | $18.0 | **$164.3 (13.8 %)** |

- **Short role cards barely matter for workers:** −50 % saves $9 in the window ($8 a week). The
  card is only about 2k tokens.
- **The harness prefix does matter.** About 26k tokens are reread on every one of 25,316 turns,
  and the `Artifact` schema alone costs $92 in the window.
- Design-2 action: worker agent definitions with a tool allowlist (Bash, Read, Edit, Write,
  Grep/Glob, SubagentHandback), no skill listing, and the Studio repo as working directory.
- Replacing the white-paper `AGENTS.md` with the Studio one (1.4k) nets 1.8k tokens, not 3.2k.
  The combined figures in §7 use the net value.

## 2. Long suites and waits

### 2.1 What workers waited for before a cache rebuild [M] (`a2_waits.py`)

| Role | Waited for | Rebuilds | Excess over a warm read | Gap 5–10 min | Median ctx |
| --- | --- | --- | --- | --- | --- |
| Coder | foreground long suite (`just visual`, `gate.sh`, integration) | 75 | **$41.75** | 70 | 155k |
| Coder | CI watch / poll | 16 | $9.94 | 15 | 229k |
| Coder | background task notification | 13 | $5.49 | 10 | 186k |
| Coder | kept alive after its own hand-back | 14 | $6.82 | 5 | 172k |
| Coder | other (writes, reads, UI drive) | 33 | $10.29 | 22 | 107k |
| Coder | fast gates | 6 | $3.50 | 4 | 140k |
| Inspector | long suite / bg / CI | 12 | $3.01 | 12 | 108k |
| Inspector | kept alive | 13 | $2.83 | 5 | 91k |
| Analyst (req) | kept alive | 14 | $13.65 | 1 | 439k |
| Writer (req) | kept alive | 20 | $7.55 | 6 | 166k |

- **Long suites cross the 5-minute TTL by seconds [M].**
  - The long-suite Bash calls behind these rebuilds last p10 304 s, p50 **325 s** and p90 501 s.
  - **49 of the 75 coder rebuilds** ($31.4) happen 300–360 s after the previous turn; 33 of them
    ($23.6) within 300–330 s.
  - These are not timeouts: 70 of the calls use `timeout: 600000`.
  - Over all 341 foreground long suites in coders and inspectors: p50 21 s, p90 326 s, 64 above
    300 s (63 of them under 600 s).
- **Outcome after the wait [M].** Pass means no source edit follows in the same agent.
  - Coder long suites: 37 pass ($20.0 excess), 38 followed by fixes ($21.7).
  - CI waits: 2 pass, 14 fixes.
  - Exit codes are masked, so this source-edit test replaces them.

### 2.2 Options, simulated event by event [S] (`a2_options.py`, `a2_ttl.py`)

Coder events: 104 events, $57.2 excess. Inspector events: 12 events, $3.0 excess.

| Option | Coder (window) | Inspector | How |
| --- | --- | --- | --- |
| (a) Coder runs the suite in the background and is notified | **$0** | $0 | The gap is unchanged, so the rebuild stays. The 13 background-notification rebuilds that exist today prove it. |
| (b) 1-hour TTL, today | **−$12.7** (cheaper) | **+$16.6** (dearer) | Every write costs 1.6×; rebuilds under 1 h become reads. |
| (b) 1-hour TTL once the waits are removed | **+$43.1** | +$19.6 | Nothing left to save. |
| (c) Coder stops after fast gates; the Driver runs `crf gate --long`. On failure, **resume** the coder | +$25.6 on pass events − $17.1 driver turns − $9.3 resume overhead = **≈ +$7–9** | +$2.1 pass − $1.8 driver | The Driver rebuild is $0.148 per event (52k context, Sonnet). Resume pays the same coder rebuild as today, plus the Driver turns. |
| (c) as above, but a **fresh coder with a hand-over note** on failure | pass saving − driver turns + **$50–53 on fail events** (≈ $70 net on long + CI + background) | +$0.4 | The fresh coder costs a cold start of $0.045–0.065 plus re-exploration (Sonnet $0.18–0.22, Opus $0.57–0.62 before its first edit [M]). It then carries a 57k context instead of 155–229k for the rest of the round. |
| (d) Shorter suites (under about 4.5 min) | **$40.0–41.0** of the $41.75 | $2.6 | Cutting 30–60 s off `just visual` / `gate.sh` already removes 49 of 75 rebuilds ($31.4). |

**Resume rebuild versus fresh cold start, per failure event [M]:**

- Resume: the coder rebuild excess averages **$0.57** (155k context: Sonnet ≈ $0.36, Opus ≈ $0.74).
- Fresh coder: about **$0.25–0.70** to its first edit, and every later turn is cheaper.
- Fresh is cheaper or equal per event, and much cheaper over the rest of the round. Its risk is
  losing what the old coder learned, which the hand-over note must carry.

**Best option per role:**

- **Coder:** (d) first, bringing long suites under about 4.5 min. It is the cheapest fix and keeps
  the coder in charge of its suite (≈ $40 a window, $37 a week).
  - Whatever stays over 5 min: (c) with a fresh coder plus note on failure. Its marginal saving
    over (d) is about $20–30 a window, mostly the CI waits.
  - CI watching leaves the coder entirely (Driver, `crf ci wait`).
  - Keep the 5-min TTL. A 1-hour TTL is only a stop-gap before (c)/(d) exist (−$13 a window).
- **Inspector:** never runs long suites. It takes the `crf gate --long` summary from the Driver
  ($2.6 window). **5-min TTL** (a 1-hour TTL costs +$17).
- **Writer, critic, analyst:** no long-suite waits. 1-hour TTL is dearer for all of them
  (+$11, +$16, +$5).

## 3. Context levers [M → S] (`a2_reads.py`, `a2_images.py`, `a2_resume.py`)

### 3.1 Read shapes

Coders already read with targeted commands:

| Coder read shape | Calls | Mean tokens | p90 | Share of read tokens |
| --- | --- | --- | --- | --- |
| `sed -n` range | 2,392 | 1,437 | 2,961 | **44.6 %** |
| `grep` | 2,885 | 619 | 1,453 | 23.2 % |
| `cat … \| filter` | 614 | 1,590 | 3,487 | 12.7 % |
| **`cat` whole file** | 259 | 2,494 | 5,427 | **8.4 %** |
| Read with a range | 68 | 3,827 | 10,620 | 3.4 % |
| `ls`/`find`/`wc` | 589 | 814 | 1,950 | 6.2 % |

Whole-file `cat` share of read tokens, by role:

- inspectors 20.9 %;
- critics 8.4 %, plus 14.1 % from whole-file Read calls;
- analysts 14.9 %.

### 3.2 Re-reads

Same file (by basename) read again in the same agent [M]:

| Role | Re-reads / file reads | Unchanged since last read | Tokens |
| --- | --- | --- | --- |
| Coder | 899 / 3,635 (25 %) | 743 | 1.23 MTok |
| Critic | 175 / 994 (18 %) | 160 | 0.55 MTok |
| Analyst | 190 / 1,020 (19 %) | 188 | 0.39 MTok |
| Inspector | 66 / 935 (7 %) | 64 | 0.09 MTok |

They are mostly *different ranges* of the same file. Removing unchanged whole-file re-reads saves
only **$1.2 in the window** [S].

### 3.3 Simulated savings in the window [S]

| Role | Targeted reads (whole-file reads over 3k tokens cut to 30 %) | Cap non-read Bash output at 1k tokens (~30 lines) | Images downscaled to ≤800 px |
| --- | --- | --- | --- |
| Coder | $8.1 | $7.6 | $3.8 (508 images, median 1440×900, ~1.5k tokens) |
| Inspector | $1.8 | $4.4 | $0.9 (380 images) |
| Writer | $2.7 | $6.0 | – |
| Critic | $4.6 | $4.4 | – |
| Analyst (req) | $8.9 | $2.8 | – |

### 3.4 Resume versus fresh between rounds [S]

The simulation uses each agent's own exploration cost and its context at the first edit.

- **Rule: resume when warm (<5 min), fresh + note when cold.**
  - Saves coders **$7.6** (14 cold resumes), writers $6.3 (20), inspectors $3.3 (13) and critics
    $1.2 (3).
  - **Analysts lose with fresh agents** (−$0.4 with a note, −$19.6 without), so analysts resume.
  - 40 of the 54 coder resumes were already warm, and should stay resumes.
- **Hand-over note on the 43 round-2+ coders:** $18.7 of re-exploration [M]; a note cutting it
  25–50 % saves **$4.7–9.3** [E].
- **Context cap (autocompact at 150k → 45k)** [S], with a capability risk:
  - coder −$85.9 (13.5 %), analyst (req) −$46.8 (27 %), critic −$19.4, writer −$15.4;
  - inspector ≈ 0, because its contexts are small.

## 4. Inspector [M] (`a2_inspector.py`)

- **Size:** 236 inspectors, median 8 turns (p90 21), $0.21 per agent at the median ($0.40 mean),
  last context 56k at the median.
  - Factory inspectors: 186, median 7 turns, $0.19 median.
- **What they do:**

  | Activity | Calls | Agents doing it | Tokens |
  | --- | --- | --- | --- |
  | Source reads beyond the diff | 1,220 | 86 % | 1.3 MTok |
  | `git diff`/`show` | 306 | 66 % | 0.83 MTok, 2.6k p50 per inspector |
  | Coder report read | 224 | 69 % | 2.3k p50 |
  | Screenshots | 224 | 28 % | 0.29 MTok |
  | Fast gates | 148 | 39 % | – |
  | `okfreq` | 111 | 31 % | – |
  | **Long suites** | 39 | **11 %** | – |

- **Verdict:** file p50 220 tokens (p90 1,362); hand-back p50 323 tokens (p90 765).
  - Verdict plus hand-back is only 20 % of inspector output.
  - **A verdict schema that halves it saves $1.3 in the window.** Its value is parsing, not tokens.
- **Diff-plus-note inspector [S]:** 4 turns over prefix + diff + report + images, no source reads,
  no gates.
  - Cost **$27.4 vs $93.9** (factory $20.9 vs $52.1).
  - It drops the source reading that 86 % do today. It is **not capability-neutral**, so it is
    left out of §7.
  - The neutral version is "diff + note first, targeted source reads allowed, no gate runs (the
    Driver's `crf gate` summary in the note)". It is covered by §3 caps and §2 (long suites);
    gate-only turns are small.
- **Verdicts by model [M]:**
  - Sonnet: 182 inspectors, 15 % FIX-REQUIRED, $0.27 each.
  - Opus: 54 inspectors, 30 % FIX-REQUIRED, $0.85 each.
  - Opus inspectors were assigned to blast-radius 2–3 CRs, so the gap in FIX-REQUIRED rate is
    confounded and says nothing about quality.

## 5. Model and effort per role [S]

Same tokens repriced; quality not measured.

| Role | Today | All Sonnet | All Opus | All Haiku 5.5 (×5 above 100k) | Turns over 100k | Thinking $ [E] | Effort: −30 % / −50 % thinking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Coder | $636.2 | $559.8 (−$76) | $775.5 | $109.9 | 57 % | $59.8 | $17.9 / $29.9 |
| Inspector | $93.9 | $79.1 (−$15) | $124.7 | $7.8 | 14 % | $10.3 | $3.1 / $5.2 |
| Writer (req) | $139.5 | $135.6 | $205.1 | $22.8 | 45 % | $17.4 | $5.2 / $8.7 |
| Critic (req) | $127.5 | = | $181.9 | $23.2 | 51 % | $14.2 | $4.2 / $7.1 |
| Analyst (req) | $174.2 | $172.2 | $241.2 | $39.7 | 79 % | $14.7 | $4.4 / $7.4 |
| Conflict fixer | $3.2 | $2.9 | $4.5 | $0.14 | 0 % | ≈0 | ≈0 |

- **Opus and Sonnet reads cost the same** ($0.20). Opus → Sonnet therefore saves only on writes and
  output: about 27 % of an Opus coder's cost.
- **Haiku 5.5 is roughly 5–15× cheaper**, even with the surcharge above 100k.
  - Inspectors (14 % of turns over 100k) and conflict fixers (contexts ~41k, $3 in total) are the
    natural candidates.
  - Coders and analysts live above 100k.
- **Effort:** thinking is 6–11 % of role cost, so lower effort is a second-order lever ($3–30 a
  window per role). It only matters for coders.
- **Data that must guard any model or effort change** (collect per role and model, before and
  after):
  - rounds per CR: mean 1.40 today; 21 % need more than one round, 9 % need 3 or more;
  - FIX-REQUIRED rate per inspector model;
  - CI failures after an APPROVE;
  - CRs reopened by the user (5 in run 1);
  - long-suite or CI failures fixed inside the coder (13–67 in factory coders);
  - "Autonomous decisions" sections later reverted.

## 6. Writer, critic and analyst (requirements work)

| Lever | Writer | Critic | Analyst (req) |
| --- | --- | --- | --- |
| Prefix cuts [S] | $16–19 | $15–18 | $13–15 |
| Role card −30 / −50 % [S] | $0.8 / 1.3 | $0.3 / 0.4 | $0.8 / 1.4 |
| Targeted reads / output cap [S] | $2.7 / $6.0 | $4.6 / $4.4 | $8.9 / $2.8 |
| Resume vs fresh [S] | fresh + note when cold: $6.3 | $1.2 | **resume** (fresh loses $0.4–19.6) |
| 1-hour TTL [S] | +$11.2 (no) | +$15.5 (no) | +$4.8 (no) |
| Context cap 150k [S] (capability risk) | $15.4 | $19.4 | **$46.8 (27 %)** |
| Haiku [S] (quality unknown) | $23 vs $140 | $23 vs $128 | $40 vs $174 |

**Analysts are the context-heavy role:**

- median context 179k, p90 412k, up to 618k (`a0cd28d93a1ed40c8`, $21.6);
- 54 turns per agent at the median;
- their main lever is smaller contexts: split the work per feature group, or cap the context.

## 7. Combined per role [S]

Simulated sequentially, so overlaps are removed: one cut list per agent, then waits and resumes
scaled by what the cuts already removed (`a2_combine.py`).

- **Low:** `Artifact` and skill listing dropped, `AGENTS.md` replaced, card −30 %, read and output
  caps half realised, waits via (c) with resume, resume rule half realised, note −25 %.
- **High:** low plus `Agent`/`ListAgents`/`ReportFindings` dropped, card −50 %, caps in full,
  images ≤800 px, (d) suites under about 4.5 min, (c) with a fresh coder on failure, resume rule in
  full, note −50 %.
- **Excluded:** model, effort, context cap, diff-only inspector. They are listed separately below.

| Role | Window cost | Prefix | Card, reads, caps, images | Waits | Resume rule + note | **Window** | **Per week** | % of role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Coder | $636.2 | $74.8–80.9 | $11.4–25.1 | $7.4–59.8 | $8.1–16.0 | **$102–182** | **$94–167** | 16–29 % |
| Inspector | $93.9 | $16.0–18.1 | $3.4–7.6 | $0.4–2.1 | $1.3–2.4 | $21–30 | $19–28 | 23–32 % |
| Writer (req) | $139.5 | $16.1–18.5 | $5.2–10.0 | – | $2.8–5.3 | $24–34 | $22–31 | 17–24 % |
| Critic (req) | $127.5 | $15.3–17.6 | $4.8–9.5 | – | $0.6–1.0 | $21–28 | $19–26 | 16–22 % |
| Analyst (req) | $174.2 | $12.9–14.6 | $6.7–13.1 | – | – | $20–28 | $18–25 | 11–16 % |
| Analyst (other) | $17.1 | $2.2–2.4 | $0.2–0.4 | – | – | $2–3 | $2–3 | 14–16 % |
| Conflict fixer | $3.2 | $1.0–1.1 | $0.1–0.2 | – | – | $1.0–1.2 | ≈$1 | 33–39 % |
| **All workers** | **$1,191.6** | | | | | **$191–306** | **$175–281** | **16–26 %** |

- **Factory-scope workers:** $475.2 in the window, saving $79–130 (17–27 %).
- **Optional levers that trade capability or quality** (window, not in the table, not additive):
  - context cap at 150k: coder $86, analyst $47, critic $19, writer $15;
  - all-Sonnet coders: $76; Sonnet inspectors: $15;
  - Haiku inspectors: about $70–86, or conflict fixers $3;
  - effort −30 % thinking: $35 across all roles;
  - diff-only inspector: $66.
- **Overlap with design-1 lever 2:** the waits column ($7–62) is the same $57 base as lever 2. Do
  not add both.

**Per CR, runs 1–3 [S]:**

| Run | CRs | Worker $/CR | Saving/CR | All-in $/CR today | Cut of all-in |
| --- | --- | --- | --- | --- | --- |
| 1 | 17 | $4.44 | $0.73–1.01 | $6.93 | 10–15 % |
| 2 | 7 | $3.70 | $0.50–0.74 | $4.86 | 10–15 % |
| 3 | 3 | $1.66 | $0.38–0.45 | $3.72 | 10–12 % |

The rest of a CR's cost is orchestration and main session (agents A1/B), plus the coder work
that is genuinely needed.

## 8. Key findings

1. **The biggest worker lever is the harness, not the role card.**
   - Every worker carries about 34k tokens of fixed prefix. 15.5k of that is the `Artifact`
     schema; 5.1k is a 32-skill listing; 2.6k is the wrong project's `AGENTS.md`.
   - Removing it saves $151–164 in the window (13.8 % of worker cost).
   - Halving the role cards saves $9.
2. **Long suites take 5:25 at the median: just past the 5-min cache.** Shaving about 30–60 s
   removes most of the $42 of coder long-suite rebuilds. Background runs do not help, and a
   1-hour TTL only helps until the waits go.
3. **On a failed long suite, a fresh coder with a note beats resuming:** about $0.25–0.70 against
   a $0.57 average rebuild, and smaller contexts afterwards. Analysts are the exception: always
   resume them.
4. **Inspectors are cheap** ($0.21 at the median). Half their cost is Opus escalations, and the
   prefix is 21 % of their cost. A verdict schema is about parsing, not tokens ($1).
5. **Coders already read in a targeted way** (`sed -n` 45 %, `grep` 23 %). Read caps and output caps
   are worth $15–30 a window, not more.
6. **Analyst contexts (p50 179k, p90 412k) are the requirements-work problem.** A 150k cap saves
   27 %, at a capability risk.

## 9. Evidence (agent ids, under `~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-…/subagents/agent-<id>.jsonl`)

- **Most expensive workers:**
  - coders `abf91f7ea342896ed` (CR 084, $20.13, 207 turns, peak 442k),
    `a66364994a6362e07` (CR 048, Opus, $16.25) and `a20d08b449b81c50b` (S4, Opus, $14.96);
  - inspectors `afba62723f2c995a6` (T44, $6.39, 78 turns) and `adad4254219d0f508` (S4, Opus, $3.62);
  - analysts `a0cd28d93a1ed40c8` ($21.59, peak 618k) and `a9cc9c67049b1ef31` ($19.34);
  - critic `a80217c33e8ef47d3` ($11.34); writer `adcf352f6002a2c86` (Opus shrink audit, $11.91).
- **Long-suite rebuilds just past 5 min:** `a76e2b0084f99ce18` (S2, gap 312 s, 322k, $1.55),
  `a57394b464793bbe3` (CR 041 r2, 316 s), `aa0579adfd96dea21` (S1, 310 s) and
  `af28a300d33293e0b` (CR 050, 335 s). Example command: `just visual > …` in `af3ebd75692f86ed6`.
- **Prefix payload:** the `prompt_snapshot` and `instructions` attachments of every worker, for
  example `affdfb349da1e620e`: tools 82k chars, white-paper `AGENTS.md` 9.8k.
- **Outputs:** `data/A2/out_anatomy.txt`, `out_payload.txt`, `out_cards.txt`, `out_waits*.txt`,
  `out_options.txt`, `out_ttl.txt`, `out_reads.txt`, `out_images.txt`, `out_resume.txt`,
  `out_inspector.txt`, `out_models.txt`, `out_cap.txt`, `out_combine.txt`, `out_fresh.txt`.

## 10. Limits

- Roles come from regular expressions on descriptions, inherited from design-1. Sub-role splits
  use workstreams.
- **Chars/token:** 3.81 is calibrated on first turns (JSON-heavy). Code may tokenise differently,
  by about ±15 % on the cut sizes.
- **Untested assumptions:** that a tool allowlist removes the `Artifact` schema and the skill
  listing for sub-agents. It is the largest lever, so verify it with one custom-agent run
  (first-turn context ≈ 10–12k expected).
- **Pass/fail:** "pass" means no source edit after the wait; a coder might have continued for other
  reasons.
- **Fresh-coder simulations** assume the same remaining work at a 57k context (the median at the
  first edit of round 2). This is optimistic for complex fixes.
- **Quality** of model, effort and cap changes is not measured; see §5 for the guard data.
- **Analysts excluded from the factory:** design-2 analysts and writers only appear in
  requirements work. Their figures come from the CR 059/060 workstream, which may not recur.
