---
title: The cos skill, specification
description: Build specification of the "cos" (Chief of Staff) skill that runs design 5 on
  Claude Desktop, its Python CLI run with uv, the production team's role cards and the
  capability references, and its evals.
status: built-0.1.0
date: 2026-10-31
---

# The `cos` skill: specification

[TOC]

- **Implements:** [design 5](01-design.md) on Claude Desktop, optimized as in
  [02-cost-detail.md](02-cost-detail.md). Team decisions: [04-team-grill.md](04-team-grill.md).
- **Replaces, when it ships:** the `change-request-factory` skill for live batches. Until then
  both live side by side; `cos` reuses its forge, commit and PR references by link.
- **Location:** `.claude/skills/cos/` in this repository. A skill must sit in
  `.claude/skills/<name>/SKILL.md` to be found; a folder `.claude/cos/` would not be loaded.
- **State:** version 0.1.0 is built. The CLI has 53 unit tests, and the deterministic global
  scenario passes 29 of 29 checks. The five LLM eval cases pass once each. Not done yet: a simulated
  batch on Desktop, a real batch.

:::{important} What the skill does
`cos` turns your main Claude Desktop session into the **Chief of Staff**. It talks with you,
keeps the backlog and the grill, and on your request starts one **Foreman** as a nested,
detached session. The Foreman owns the **team**: Drivers, a stack driver and a QA driver as
background subagents, each running Investigators, Coders, Inspectors, Debuggers, Verifiers and
Conflict resolvers in the foreground. Every mechanical step is a `cos` CLI command; every LLM is
there for judgement. **If one preflight condition fails, nothing starts and nothing falls back.**
:::

## 1. Scope

| In scope | Out of scope |
| --- | --- |
| Claude Desktop, Code tab, macOS and Linux | Claude Code in VS Code and the terminal: preflight fails |
| Live batches you ask for in the Chief of Staff | Batches started by cron or by another session |
| Backlog, grill, CRs, parallel CRs, stacks, CI watching, QA pass, landing | Copilot (design 5, section 4: separate skill once probed) |
| The `cos` CLI: state, events, waits, gates, ship, cost | Merging: always yours |
| GitHub through `gh` | GitLab: the CLI refuses it with exit 4 for now |

## 2. The team

Each role has a card in `references/roles/`. A card holds only what a 5.5 model would not do on
its own from the role's intent: host mechanics, ownership, batch invariants
([04-team-grill.md](04-team-grill.md)).

| Role | Runs as | Owner | Cache | Capabilities |
| --- | --- | --- | --- | --- |
| Chief of Staff | your Desktop session | you | 1 hour | `preflight`, `sessions`, `backlog-and-grill`, `batch-brief`, `steering`, `recovery`, `cost`, `events-and-state` |
| Foreman | nested session, detached | Chief of Staff | 1 hour | `batch-orchestration`, `events-and-state`, `messaging`, `sessions`, `recovery`, `cost`, `safety` |
| CR Driver | background, `cr-driver.md` | Foreman | 1 hour | `drive-cr`, `events-and-state`, `waits-and-ci`, `ship-and-forge`, `messaging`, `safety` |
| Stack driver | background, `stack-driver.md` | Foreman | 1 hour | `stack`, `ship-and-forge`, `waits-and-ci`, `events-and-state`, `messaging`, `safety` |
| QA driver | background, `qa-driver.md` | Foreman | 1 hour | `qa`, `evidence`, `events-and-state`, `messaging`, `safety` |
| Investigator | foreground, `investigator.md` | a Driver | 5 minutes | `code-round`, `safety` |
| Coder | foreground, `coder.md` | a Driver | 5 minutes | `code-round`, `gates`, `safety` |
| Inspector | foreground, `inspector.md` | a Driver | 5 minutes | `inspect`, `gates`, `safety` |
| Debugger | foreground, `debugger.md` | a Driver | 5 minutes | `gates`, `waits-and-ci`, `safety` |
| Verifier | foreground, `verifier.md` | a Driver | 5 minutes | `gates`, `evidence`, `safety` |
| Conflict resolver | foreground, `conflict-resolver.md` | a Driver or the stack driver | 5 minutes | `ship-and-forge`, `gates`, `safety` |

**Models are placeholders.** `$COS setup` writes each agent file's `model:` from
`models.<role>` in `.agents/cos.json`, `inherit` when unset. The brief's **Models** line may name
a model per CR; the Foreman or Driver passes it as the spawn's `model`. Nothing escalates on its
own.

Rules carried from design 5, with the others in `references/principles.md`:

- **Only a session owns live background agents.** The Chief of Staff owns none; the Foreman owns
  all Drivers. A Driver owns one foreground child at a time.
- **Only you start sessions.** The Chief of Staff starts the Foreman in the turn of your go.
- **Each role does only its own row.** A failing child is restarted, never replaced by its parent.
- **The one who checks never wrote it.** The Verifier and the Inspector are fresh agents.

## 3. Capabilities

A capability is one thematic reference under `references/capabilities/`, with the sections
*Purpose*, *Who uses it*, *Commands*, *Rules*, *Failure handling*. An agent reads only the ones
its agent file names.

| Capability | Covers |
| --- | --- |
| `preflight` | P1–P7, the failure block, no fallback |
| `sessions` | `start_session` with the epoch, `detach_session` and its failure, messages, latency |
| `backlog-and-grill` | inbox, P1–P4, grill questions with a recommended answer |
| `batch-brief` | `cos open`, the brief and its Models line, slots, budget, night policy card |
| `steering` | `cos order` and its order ids, what you may type in the Foreman |
| `batch-orchestration` | the event → `cos event` table, the action lines, the 3300 s heartbeat, landing |
| `events-and-state` | every state command, exit codes, state files |
| `messaging` | who may message whom |
| `drive-cr` | rounds, round limit, children, hand-back |
| `code-round` | one round, hand-over note, never commit |
| `inspect` | verdict format, blocking vs minor, read-only |
| `gates` | `cos gate` fast and long |
| `waits-and-ci` | `cos wait ci`, CI classification, re-runs |
| `ship-and-forge` | `cos ship`, PR body, conflicts to the Conflict resolver |
| `stack` | stack order, restack after merges |
| `qa` | the QA pass on a green CR, findings |
| `evidence` | reproduce first, screenshots, assets |
| `recovery` | liveness check, orphans, resume on your word |
| `safety` | permissions, classifier refusals, environments, scratch files |
| `cost` | `cos cost`, `--update` at each heartbeat, budget stop |

## 4. Skill layout

```text
.claude/skills/cos/
├── SKILL.md                      entry points, hard rules, team table, cos-version
├── references/
│   ├── roles/                    one card per role, and README (model placeholders)
│   ├── principles.md             eleven non-obvious rules, each with its reason
│   ├── capabilities/             one file per capability (section 3)
│   └── message-formats.md        the only definition of the one-line formats
├── playbooks/README.md           empty on purpose; format for a playbook added later
├── assets/agents/                nine templates rendered by `cos setup` into .claude/agents/
├── cli/                          the uv project of the `cos` CLI
│   ├── pyproject.toml            name "cos", Python >= 3.11, no runtime dependency
│   ├── src/cos/                  cli, commands, decide, state, forge, procs, costs
│   └── tests/                    pytest, temp git repos, a fake gh
└── evals/                        global scenario and claude plugin eval cases (section 11)
```

`$COS` is `uv run --script <skill folder>/cli/cos.py` with the absolute skill folder (a PEP 723 script with no dependency: no virtual environment, no build, no network); `cos setup`
writes that absolute prefix into every agent file, so agents work from a CR worktree too.

## 5. Entry points in `SKILL.md`

| You ask… | The Chief of Staff | Capabilities |
| --- | --- | --- |
| "set up cos" | `$COS setup`, then asks you to restart the session if agent files changed | `preflight`, `batch-brief` |
| to file or triage an item | backlog commands | `backlog-and-grill` |
| "run the P1s", a batch, a stack | preflight → grill → `$COS open` → start and detach the Foreman | `preflight`, `batch-brief`, `sessions` |
| "status?" | `$COS status`, with links; a blocked CR comes back as a question | `events-and-state` |
| add, drop, reorder, change a CR; "I merged #42" | `$COS order …`, then its line to the Foreman | `steering` |
| "I restarted the app", "resume" | liveness check; on your word, preflight and a new Foreman | `recovery` |
| "what did it cost?" | `$COS cost` | `cost` |

## 6. Preflight

| # | Condition | Checked by | How |
| --- | --- | --- | --- |
| P1 | Host is Claude Desktop | CLI | `CLAUDE_CODE_ENTRYPOINT == "claude-desktop"` |
| P2 | Session tools exist | Chief of Staff | `ToolSearch` loads `start_session` and `detach_session` |
| P3 | Your go is in this turn | Chief of Staff | the final go, after the grill, is in your own message of this turn |
| P4 | Agent files installed and current | CLI | the nine files exist, carry the CLI's template version, `cacheTtl: 1h` on the three Drivers |
| P5 | CLI ready | CLI | `uv` found; `cos-version` in `SKILL.md` equals the CLI version |
| P6 | Main checkout, cos set up | CLI | the session folder is the repository root and `.agents/cos.json` exists |
| P7 | Not a linked worktree, not unattended | CLI and Chief of Staff | `--git-dir` equals the common dir (else `detach_session` would refuse); a person is at the keyboard |

`$COS preflight` exits `0` only if P1 and P4–P7 pass, and ends with
`preflight FAILED: start nothing` otherwise. The Chief of Staff then prints the failure block
and ends its turn: **no `cos open`, no session, no agent, no other design.**

## 7. The `cos` CLI

### 7.1 Contract

- **Python ≥ 3.11, standard library only**, run with `uv run`. The only external calls are `git`
  and `gh` (`COS_GH` names another executable; the tests use a fake one).
- **Short output.** At most 10 lines by default, `--json` on `status` for the full record.
- **Exit codes:** `0` done, `1` usage, `2` precondition, `3` stale Foreman epoch, `4` external
  failure (git, gh, a gate, a failed CI wait), `5` budget.
- **State is code-owned.** Only the CLI writes `batch.json` and `events.jsonl`, under an `fcntl`
  lock (30 s timeout), by atomic rename; every change appends events.
- **Batch resolution:** `--batch`, else `COS_BATCH`, else the latest open batch; a CR id finds
  its own batch. `COS_ROOT` overrides the repository; from a linked worktree the CLI finds the
  main repository through `git rev-parse --git-common-dir`.
- **Foreman epoch.** `foreman set` increments it; every Foreman command passes `--epoch`; a stale
  one exits 3 and stops.

### 7.2 State

```text
<changes folder>/batches/<batch-id>/
├── batch.json        CRs, order, slots, budget, spent, Foreman id and epoch, agent ids, orders
├── events.jsonl      append-only log
├── brief.md          skeleton written by `cos open`, completed by the Chief of Staff
├── report.md         written by `cos land`
└── crs/<cr>/         task.md, STATE.md, pr-body.md, scratch/ (gate logs, round notes, diagnosis)
<changes folder>/.cos-counter   CR numbers, unique in the repository, from CR-101
.agents/cos.json                config: changes_dir, default_branch, remote, worktrees_dir,
                                forge, max_rounds, stale_minutes, gates.fast/long, models
.agents/cos-installed.json      hashes of the agent files setup wrote (local edits are kept)
```

### 7.3 Commands

| Command | Called by | Does |
| --- | --- | --- |
| `setup [--force]` | Chief of Staff | writes `cos.json`, renders the nine agent files; keeps local edits unless `--force` |
| `preflight` | Chief of Staff | P1, P4–P7 |
| `open <batch> <item>… [--slots N] [--budget USD] [--stack] [--qa all\|1,3] [--no-worktrees] [--cos ID]` | Chief of Staff | batch, CR folders, branches and worktrees from the fresh default branch, brief skeleton |
| `add <title\|@file> [--qa]` | Foreman (through order-add) | one queued CR with its worktree |
| `order <kind> [<cr>] [--note T]` | Chief of Staff | records an order, prints `[cos→foreman] order O-<k> …` |
| `foreman set\|get\|transcript [<value>]` | Chief of Staff, Foreman | the Foreman's id and epoch; its transcript uuid for `cost` |
| `status [--notes] [--json]` | anyone | one line per CR; a blocked CR shows its reason |
| `agents set\|get <cr\|stack\|qa:cr> [<agent-id>]` | Foreman | agent ids |
| `event <kind> [<cr>] [<note>]`, `event --order O-<k>` | Foreman | the decision table (7.4) |
| `report <cr> <kind> [<note>]` | Drivers | `pr-opened`, `ci-green`, `ci-red`, `ci-red-known`, `round-done`, `note` |
| `heartbeat` | Foreman | live CRs, pending orders, oldest silence |
| `gate <cr> [--long]` | Coder, Driver | the configured gates in the worktree, each in its own process group (recorded for `cancel`) |
| `wait ci <cr> [--max S]` | Driver, in the background | polls `gh pr checks` outside the LLM; records its pid |
| `ci classify <cr>` | Driver | `none`, `known-red-on-main`, `infra` or `product` |
| `ship <cr> [--title T]` | Driver | refuses tracked changes, rebases (on the CR below in a stack), pushes with lease, opens or edits the PR |
| `stack order <cr>…`, `stack restack` | stack driver | order; re-ship every open PR of the stack |
| `qa start\|done <cr> [--findings F]` | QA driver | records the pass and counts the findings |
| `cancel <cr>` | Foreman, after `TaskStop` | kills recorded process groups and pids, then any process in the worktree; fills the slot |
| `land` | Foreman | refused while a CR is live, queued, ready or blocked, an order is pending, or the stack driver lives; removes worktrees and branches, writes `report.md` |
| `cost [--by role\|cr] [--update] [--transcript UUID]` | anyone; Foreman with `--update` | prices the Foreman's transcript and its subagents |

### 7.4 `event` actions

| Event | Actions printed |
| --- | --- |
| `start`, `tick` | `spawn <cr>` for free slots (tick also `message <cr> ping…` past `stale_minutes`) |
| `hand-back-ready <cr> [link]` | QA CR: `spawn qa:<cr>`; stack mode when all are ready: `spawn stack` or `message stack restack`, then `ask-cos stack-ready …`; else `ask-cos ready <cr> <link>`; plus slot fills |
| `hand-back-blocked`, `question` | `ask-cos blocked …`, `ask-cos question …` |
| `anomaly <cr> <text>` | Driver alive: `message <cr> round …`; Driver ended: `spawn <cr> resume round: …`; past `max_rounds`: `ask-cos blocked …` |
| `qa-done <cr> <n>` | findings: `none` (an anomaly follows); none: as a ready hand-back |
| `driver-done <cr\|stack\|qa:cr>`, `driver-lost <cr>` | after a hand-back: `none`; else `spawn <cr> resume`, blocked after 2 resumes |
| `--order O-<k>` | `ok O-<k> …` plus: add → a new CR; drop → `cancel <cr>` if live; first, change, merged (→ `land` when all merged), pause, resume; a done order prints `ok O-<k> already done` |
| any, once landed | `none landed` |
| budget reached | `ask-cos budget <spent>/<budget>` once; no spawn until `resume` |

The Foreman carries out the lines in order and decides nothing else.

## 8. Agent templates

`assets/agents/*.md` are rendered by `cos setup` into `.claude/agents/`, because a session reads
agent files only from there and only at start (P4). Placeholders: `{{COS}}` (the absolute
prefix), `{{SKILL}}` (the skill folder), `{{MODEL}}` (`models.<role>` or `inherit`). Each
template names its tools, `background: true` and `experimental.cacheTtl: 1h` for the three
Drivers, its role card, the principles and its capabilities, and a version line
`# cos-template: <version>` that P4 compares.

The Foreman has no agent file: it reads its role from the start line
`/cos foreman <batch> --cos <Chief of Staff session id> --epoch <n>`.

## 9. Messages

The only definition is `references/message-formats.md`. Orders from the Chief of Staff carry the
order id `cos order` printed, so a repeated order is done once. Drivers message only the Foreman;
the Foreman messages a Driver by agent id; nobody messages a foreground child.

## 10. Requirements

| ID | Requirement | Acceptance | Covered by |
| --- | --- | --- | --- |
| COS-01 | The skill lives in `.claude/skills/cos/` and loads as `/cos` | `/cos` in a Desktop session's skill list | seen in this session |
| COS-02 | Preflight is all or nothing, with no fallback | in VS Code, a batch request prints the failure block naming P1 and P2, and starts nothing | unit tests, scenario, eval `refuses-outside-desktop`; VS Code run still to do |
| COS-03 | The Foreman starts only in the turn of your go, then is detached | `get_session` shows `detached: true`; no app note afterwards | Desktop run to do |
| COS-04 | Models are placeholders | agent files carry `models.<role>` or `inherit` | unit test |
| COS-05 | Drivers from agent files with a one-hour cache | Driver transcripts show only one-hour writes | P4 check; Desktop run to do |
| COS-06 | One `cos event` per event, the Foreman decides nothing else | median model calls per Foreman event ≤ 2 | decision-table tests; Desktop run to do |
| COS-07 | Routine milestones go to `cos report` | Foreman events per CR ≤ 3 | scenario |
| COS-08 | State only through the CLI, locked and atomic | 24 concurrent `report` processes leave 24 notes and events | unit test |
| COS-09 | At most 10 lines by default | output test | unit test |
| COS-10 | Waits run outside the LLM | `cos wait ci` polls in the CLI | unit test |
| COS-11 | A cancel leaves no process behind | stray and grouped processes are gone | unit test, scenario |
| COS-12 | Refusals are reported, never worked around | a refused action appears once with its text | Desktop run to do |
| COS-13 | Recovery needs your word | after a restart the Chief of Staff asks first | Desktop run to do |
| COS-14 | Cost is measured | `cos cost` prices transcripts like `claude_usage.py` | pricing unit tests |
| COS-15 | Never merge, never start a backlog item alone | `land` refused until every CR is merged or cancelled | unit test, scenario |
| COS-16 | A stale Foreman stops | a command with an old epoch exits 3 | unit test, scenario |
| COS-17 | Orders are idempotent | an order read twice is done once | unit test, scenario |

## 11. Tests and evals

1. **CLI unit tests** (`uv run --project cli pytest`, 53 tests): setup and placeholders, the
   preflight matrix (`claude-desktop`, `claude-vscode`, `cli`, none, missing agent file, no
   1-hour cache, linked worktree), the decision table, orders, epoch, gates, ship (parallel and
   stack), CI waits and classification, cancel, land, locking, output size, batch resolution,
   pricing and cost.
2. **Global scenario** (`python3 evals/scenario/run_scenario.py`, 29 checks): one batch of five
   CRs end to end through the real CLI with a scripted Foreman and Drivers, a bare origin and a
   fake `gh`.
3. **Behavior evals** (`claude plugin eval . --scaffold --allow-tools Bash --judge-model sonnet`):
   five cases (see `evals/README.md`), including one where the skill must not fire. On
   2026-10-31, one run each with an Opus 5.5 agent: 5 of 5 pass. Three runs per case and Sonnet
   or Haiku agents are not run yet. Per-rule ablation evals come
   later ([04-team-grill.md](04-team-grill.md)).
4. **Still to do:** the VS Code acceptance (COS-02), a simulated batch on Desktop (COS-03, 05,
   06, 12, 13), then a real batch of 2–3 CRs priced with `cos cost` against
   [02-cost-detail.md](02-cost-detail.md).

## 12. Open questions

1. **Copy or link change-request-factory's forge, commit and PR references?** Recommended: link
   until `cos` replaces it, then move them into `cos`.
2. **QA per stack?** The CLI runs QA per CR only. Recommended: add a stack-level QA pass only if
   a real stack batch shows per-CR QA misses integration bugs.
3. **Should `cos` also replace the name `crf` in designs 2 to 5?** Recommended: yes in the skill;
   the designs keep `crf` as written.
4. **GitLab.** Recommended: add `glab` in `forge.py` when a GitLab project needs `cos`.
