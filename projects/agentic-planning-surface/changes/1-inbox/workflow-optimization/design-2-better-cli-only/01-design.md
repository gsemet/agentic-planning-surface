---
title: A cheaper change-request factory with a better CLI, design 2
description: Today's agent tree unchanged; a crf command-line tool takes over mechanical work and waits. Exploratory, not a change spec.
status: exploratory
date: 2026-10-28
---

# A cheaper change-request factory with a better CLI: design 2

[TOC]

- **Scope:** tools only. The agents, their places in the tree, their models and their caches stay
  as today. Sessions, agent files and cache settings belong to
  [design 3](../design-3-sibling-session/01-design.md).
- **Follows:** [01-handoff.md](../01-handoff.md) and
  [design 1](../design-1-dynamic-workflow/03-design-sketch.md), set aside because it replaced
  agents with a workflow script.
- **Evidence:** [evidence/](evidence/), five reports measured on the runs of 2026-10-17 to 27,
  plus one CLI-only simulation, [z_cli_only.py](evidence/scripts/A1/z_cli_only.py).
- **Target:** the generic skill
  [change-request-factory](../../../../../../.claude/skills/change-request-factory/SKILL.md).

:::{important} Goal and verdict
Give today's factory a command-line tool, `crf`, and change nothing else. Every agent calls it
for mechanical work: opening CRs, status, ship, gates, CI waits, stacks, landing.

Simulated on ten days of real turns at official prices, `crf` alone should save
**$72–200 a week, 5 to 15 %** of about $1,325. All 44 capabilities seen in those sessions stay.

It cannot fix the largest cost of the orchestrator. As a subagent, the orchestrator has no
`/loop` and a five-minute cache, and it sits blocked while its Drivers run. Each wake after five
minutes rebuilds its whole context. That is 60 % of its cost today, and no tool reaches it.
:::

## 1. What ten days of runs show

| Finding | Measured | What a tool can do |
| --- | --- | --- |
| Agents spend turns on mechanics | 3.5 to 7.5 turns per ship; 475 CI watch commands; 561 `sleep` calls | One `crf` call per chain of mechanical turns |
| The main session reads state by hand | 452 status-reading turns, $38 in the window | `crf status`: a few lines per CR |
| The main session writes ad hoc scripts | 217 turns, $19 | `crf open`, `crf ci`, `crf land` |
| Hand-backs and status files are long | The orchestrator carries 498 hand-backs, 85 turns each | A 300-token hand-back schema, checked by `crf` |
| Long test suites run inside the coder | Median 5 min 25 s; 49 of 75 coder rebuilds came 300 to 360 s after the suite started | `crf gate --long`, run by the Driver |
| The orchestrator rebuilds after each child | Rebuild writes are 60 % of its cost; 61 rebuilds follow a hand-back | Nothing: the wait is an open `Agent` call, not a command |

Sources: [A1](evidence/A1-orchestration-costs.md) for the orchestrator, Drivers and main session,
[A2](evidence/A2-worker-costs.md) for coders and reviewers,
[B](evidence/B-capabilities.md) for capabilities, and
[C](evidence/C-mechanisms.md) for what Claude Code and Copilot document. Prices from
[prices-corrected.md](evidence/prices-corrected.md).

## 2. The design in one picture

:::{figure} diagrams/agent-tree.svg
:label: fig-tree
:alt: Today's tree. The main session, with a one-hour cache, spawns the orchestrator as a subagent at depth 1, with a five-minute cache, no /loop, blocked while its Drivers run. Drivers at depth 2 spawn the Coder and Reviewer at depth 3, the depth limit. Every agent calls the crf command-line tool for open, status, ship, gates, waits, stacks, notes and landing.

The agents of today, unchanged. Only the tool they call is new.
:::

| Role | Runs as | Cache | Uses `crf` for |
| --- | --- | --- | --- |
| Main session | your conversation | 1 hour, main-conversation default | `open`, `status`, `note`, `land` |
| Orchestrator | subagent of the main session | 5 minutes | `status`, `slots`, `stack`, reading hand-backs |
| Driver, stack and task Drivers | subagents of the orchestrator | 5 minutes | `ship`, `gate --long`, `ci wait`, `wait`, `stack` |
| Coder | subagent of a Driver, fresh per round | 5 minutes | `gate` (fast gates only), `handover` |
| Reviewer | subagent of a Driver | 5 minutes | `gate` summary |

## 3. What the CLI cannot fix: the orchestrator's cache

The orchestrator is a subagent. Three documented limits follow, and no tool lifts them:

- **It cannot wake itself.** `ScheduleWakeup`, the tool behind `/loop`, is withheld from every
  subagent, and background subagents keep no Cron tool
  ([sub-agents](https://code.claude.com/docs/en/sub-agents)). A keep-warm tick is not possible.
- **It sits inside one open call.** "By default the spawning subagent waits for each nested
  subagent's report"
  ([sub-agents](https://code.claude.com/docs/en/sub-agents#let-subagents-spawn-their-own-subagents)).
  In the spikes of 2026-10-28, 783 of 783 spawns from a subagent returned only with the child's
  report. A background `crf wait` cannot run beside that call.
- **Its cache lives five minutes.** Subagents write five-minute cache entries by default, and a
  Driver round takes longer than that.

So every hand-back that arrives more than five minutes after the spawn rebuilds the
orchestrator's whole context. In the ten days, that was 61 rebuilds and $31 in the window.
`crf` makes that context smaller, which makes each rebuild cheaper, but the number of rebuilds
stays.

:::{note} What /loop and a one-hour cache would add
The full design 2, before this rewrite, gave the orchestrator its own session with a one-hour
cache and a `/loop` tick. Simulated after the other levers, that alone was worth **$13–18 a
week** on the orchestrator. Design 3 tests a cheaper way to get it, the Foreman in a second tab.
:::

Drivers can still keep their own cache warm. A Driver waiting for CI calls `crf wait --max 270`
in the foreground: it returns before the five-minute cache expires, and the Driver calls it
again. A background wait across turns does not work at this depth: in the same spikes, a nested
child's background shell was killed when the child ended its run.

## 4. The `crf` command-line tool

A Python script run with `uv run` and PEP 723 inline metadata, in the skill folder, shared by
every agent. It prints 10 to 30 lines, writes the state, and owns exit codes: today, coders mask
them with `; echo exit $?`. All names are working names.

| Command | Does | Replaces, measured |
| --- | --- | --- |
| `crf open <items…>` | CR folders, briefs, state, worktrees, IDs allocated up front | ad hoc batch scripts; ID clashes on rebase |
| `crf status [--notes]` | A few lines per CR, with links, heartbeats and ages | 452 status-reading turns in the main session |
| `crf ship <cr>` | Explicit-path commit, rebase, push, PR from `pr-body.md` | 3.5 to 7.5 Driver turns per call |
| `crf gate <cr> [--long]` | Runs the project's gates; summary, verdict, log path | long suites inside the coder |
| `crf ci wait\|heavy\|classify` | Waits for CI, dispatches heavy CI, flags flakes by rule | 475 watch commands and 561 `sleep` calls |
| `crf wait [--max <s>]` | Exits on a CI result, a merge, or the deadline | LLM polling |
| `crf stack order\|check\|sync\|bisect` | Builds and checks the chain, restacks after merges, bisects a red top | stack Driver turns; the one base cycle |
| `crf handback`, `handover` | Writes and checks the 300-token hand-back and the coder's hand-over note | free-form reports |
| `crf note`, `add`, `cancel`, `order`, `grant`, `hold`, `pause`, `resume`, `slots` | Steering, written to the state, read at the next wake | relayed messages that waited for a blocked orchestrator |
| `crf deps sync`, `lock`, `awake`, `deny` | Private `npm ci`, window-test lock, keep-awake, denied commands for you | five ad hoc fixes of the last runs |
| `crf land <cr>` | Report, archive, a cleanup script you run | landing turns |
| `crf render`, `lint`, `measure` | Generated tracking files, checks, cost per agent tag | stale status files; the cost scripts |

Steering through the state does not make the orchestrator reachable sooner. It means a note
is never lost: the orchestrator reads `crf status --notes` at its next wake, instead of the main
session re-sending a message that never arrived (14 of 89 did not).

## 5. Each agent, with the tool

- **Main session:** answers status questions with one `crf status` call, opens a batch with
  `crf open`, steers with `crf note`. It still talks with you, grills, triages and reacts to the
  orchestrator's hand-backs as today.
- **Orchestrator:** reads `crf status` instead of status files, and 300-token hand-backs
  instead of full reports. It still waits inside its `Agent` calls.
- **Drivers:** ship, gate, wait for CI and restack through `crf`. Each call replaces 3.5 to 7.5
  turns. Long suites move from the coder to `crf gate --long`, run by the Driver. On failure, the
  Driver starts a fresh coder with a `crf handover` note: $0.19–0.70, against a $0.58 average
  rebuild for resuming the old one.
- **Coder:** runs fast gates only, then ends its round. Your mid-round redirection works as
  today: the Driver resumes the same coder with `SendMessage`.
- **Reviewer:** reads the diff, the coder's note and the `crf gate` summary, and the source where
  needed. 86 % of reviewers read source beyond the diff; that stays.

## 6. Expected saving

Weekly figures at official prices. Dark bars are the low case, light bars the high case:

```vega-lite
width: 560
height: 200
data:
  values:
    - {item: "Orchestrator", low: 14, high: 42}
    - {item: "Drivers", low: 14, high: 34}
    - {item: "Main session", low: 28, high: 54}
    - {item: "Coders and reviewers", low: 16, high: 69}
    - {item: "Total, crf alone", low: 72, high: 200}
encoding:
  y: {field: item, type: nominal, sort: null, title: null}
layer:
  - mark: {type: bar, color: "#C9E8CF"}
    encoding:
      x: {field: high, type: quantitative, title: "Saving per week, dollars"}
  - mark: {type: bar, color: "#46a758"}
    encoding:
      x: {field: low, type: quantitative}
```

```{list-table} Saving per week from crf alone, at official prices
:header-rows: 1
:widths: 24 44 16 16

* - Part
  - `crf` levers
  - Base per week
  - Saving
* - Orchestrator
  - mechanical chains collapsed, `crf status`, 300-token hand-backs; no keep-warm
  - $89
  - **$14–42**
* - Drivers
  - the same, plus `crf wait --max 270` in the foreground during CI waits
  - $92
  - **$14–34**
* - Main session
  - status reads, ad hoc scripts, landing and monitoring turns replaced by `crf`
  - $183
  - **$28–54**
* - Coders and reviewers
  - long suites in `crf gate --long`; fresh coder with a `crf handover` note on failure
  - $565
  - **$16–69**
* - **Total**
  - **5 to 15 % of about $1,325 a week**
  -
  - **$72–200**
```

How each figure was obtained:

- **Orchestrator and Drivers [S].** The turn-level simulator of
  [A1](evidence/A1-orchestration-costs.md) replays every real turn with a five-minute cache, no
  compaction and no tick for the orchestrator. Drivers re-arm only after a `crf wait`, never while
  blocked on a child. The low case collapses only git and status chains of three turns or more; the
  high case collapses every mechanical chain of two or more. The baseline reproduces the billed cost
  within 1.5 %.
- **Main session [S, scaled].** The [A1](evidence/A1-orchestration-costs.md) section 8 simulation,
  restricted to the turn causes `crf` replaces: status reads, ad hoc scripts, landing, monitoring.
  These are 73 % of its orchestration cost. Relays, restarts and reactions to notifications stay.
- **Coders and reviewers [S].** The waits and fresh-coder levers of
  [A2](evidence/A2-worker-costs.md) section 7. The tool allowlist and prefix cuts are not counted:
  they need agent files.

:::{warning} Where the high case is optimistic
It assumes the orchestrator never reads a file beyond `crf` output. In the requirements batches,
many of its reads were hand-back report files. The range is wide on purpose.
:::

### 6.1 Against the full design 2

| | `crf` only (this design) | Full design 2, before this rewrite |
| --- | --- | --- |
| Saving per week | $72–200 | $222–413 |
| Changes | one CLI | CLI, agent files, compaction, one-hour cache, Foreman in its own session |
| Orchestrator cache | 5 minutes, rebuilt at each late hand-back | 1 hour with a `/loop` tick |
| Risk | low: no change to the agent tree | young features: background sessions, cross-session messages |

The $150–213 a week left on the table comes from three things a CLI cannot do: agent files with
a tool allowlist (the 15.5k-token `Artifact` schema in every worker turn), compaction at 100k,
and a cache that outlives a Driver round. `crf` is the first step of both other designs, so
nothing built here is thrown away.

## 7. Copilot CLI

`crf` is a plain command-line tool, so it runs the same under Copilot. Output over 20 KiB is
spilled to a file there, so the 10-to-30-line rule matters less but still saves context. Copilot
documents no one-hour cache and no self-wake for subagents either; the orchestrator's limit is the
same on both.

## 8. Capabilities kept

The capability audit lists 44 things the factory or you relied on in ten days
([B, section 2](evidence/B-capabilities.md)). Design 2 keeps all of them, since no agent moves.
Two high-risk ones stay as weak as today:

| Risk in the audit | Capability | With `crf` |
| --- | --- | --- |
| High | Talking to a running orchestrator quickly | Unchanged: messages wait for its open call. `crf note` makes sure they are not lost |
| High | Restarting the orchestrator without killing its Drivers | Unchanged. A new orchestrator rebuilds its view from `crf status` faster |

## 9. Spikes before building

Each spike is a short real run with a pass criterion.

1. **Foreground re-arm in a Driver.** A Driver under a subagent orchestrator calls
   `crf wait --max 270` twice across a 9-minute CI wait. Pass: the turn after each call reads the
   cache instead of rebuilding it.
2. **`crf ship` and `crf gate --long` on one real CR.** Pass: the Driver's mechanical turns per CR
   drop from 5 to 2 or fewer, and the coder never runs a suite over a minute.
3. **`crf status` in the main session.** One batch with status questions. Pass: one call per
   question, no file reads.
4. **Copilot CLI.** The same `crf` drives one CR. Pass: same commands, same exit codes.

## 10. Risks

:::{warning} What could keep the saving low
- **Agents keep their habits.** The saving needs the skill and briefs to require `crf`; an agent
  that still writes its own `git` chain saves nothing.
- **The orchestrator's rebuilds remain.** 60 % of its cost does not move with a CLI.
- **The high case is optimistic.** See section 6.
- **The prices.** Every figure assumes API rates on a subscription; the saving buys more work
  within the same plan limits.
:::

## 11. Decisions and open questions

Decided on 2026-10-27:

1. **Where does `crf` live?** A script in the skill folder, shared by every agent.
2. **One orchestrator per batch or one long-lived one?** One per batch, named after it; a batch
   is the unit you start, steer and land.

Open:

1. **Which commands first?** Recommended: `status`, `ship` and `gate --long`. They carry most of
   the turns dropped in the simulation.
2. **Which project change first?** Recommended: shorter long suites in the Studio. They cut coder
   rebuilds with no skill change at all.
