---
title: A cheaper change-request factory, design sketch
subtitle: Exploratory, not a change spec
date: 2026-10-27
---

# A cheaper change-request factory: design sketch

- **Date:** 2026-10-27
- **Status:** **design 1, set aside** on 2026-10-27. Kept for reference; design 2 keeps the
  agent layers instead of replacing them with a workflow.
- **Inputs:** [01-handoff.md](../01-handoff.md), [02-research.md](02-research.md)
- **Evidence:** [evidence/](evidence/), four reports on the runs of 2026-10-17 to 27
- **Target:** the generic skill
  [change-request-factory](../../../../../../.claude/skills/change-request-factory/SKILL.md)

:::{note} Scope
The goal is to make the skill cheaper while keeping every feature: the main session as the
user's Chief of Staff, free of orchestration, parallel CRs, coder and reviewer rounds, backlog,
grill, stacked PRs, CI watching, landing and the demo tour. It must run on Claude Code and on
GitHub Copilot CLI, which the research shows is where VS Code is heading. The Studio project is not migrated yet.
:::

## 1. Where the money goes

:::{figure} diagrams/cost-drivers-levers.svg
:label: fig-cost
:alt: Three bars: long contexts reread every turn 546 dollars or 40 percent, cache rebuilds after waits 234 dollars or 17 percent, shell reads carried to the end about 180 dollars or 13 percent, each with the lever aimed at it.

Measured cost drivers of one week of runs and the lever the sketch aims at each one. Source:
`rapport-cout-orchestration.en.md` in the Studio repository, folder
`.agents/changes/01-inbox/cost-analysis/`.
:::

The three drivers have one thing in common: an LLM context that stays open while nothing needs
judgment. The orchestrator rereads its long context on every tick. A driver keeps its context
open while CI runs, so the cache expires. A coder keeps every file it read until it finishes.
A fourth cost hid in the main session: 43 % of it went to orchestration (section 3.2).

## 2. The idea in one picture

**Keep an LLM only where judgment is needed. Move everything else into code.** The orchestrator
and the drivers become a workflow script that asks a small state machine, `crf`, what to do next.
Waiting, gates, commits, pull requests, CI and the stack run inside `crf`. The coder and the
reviewer stay LLMs. A **judge**, a fresh LLM agent started per event, takes the decisions that
the orchestrators and drivers improvised.

**The main session becomes a Chief of Staff.** It talks with you, turns your wishes into `crf`
commands and wakes only when a CR needs your decision. It no longer reads status files, polls
GitHub, relays messages or restarts agents. Ten days of transcripts show why this matters: 43 %
of the main session's cost went to that orchestration work.

:::{important} `crf-build` is a workflow, not a command-line tool
`crf-build` and `crf-land` are workflow files that the harness itself runs inside the current
session: the main session starts them with its `Workflow` tool on Claude Code, or by name on
Copilot. Their coder, reviewer and judge are ordinary subagents of that session. They follow the
session's permission rules and show up in `/workflows`. The `crf` CLI never starts an LLM.
`claude -p` appears only for a night batch started by cron with no session open, and even then
a full Claude Code session launches the same workflow.
:::

:::{figure} diagrams/agent-tree-before-after.svg
:label: fig-tree
:alt: Left, today: main session that also orchestrates, orchestrator, one driver per CR, coder and reviewer, all LLMs. Right, sketch: main session as Chief of Staff steering through crf, crf-build and crf-land workflows, coder, reviewer and judge LLMs, an opt-in interactive coder, and the crf state machine underneath.

Today's agent tree and the sketch. Hatched roles are replaced by code; dashed arrows are your
steering, through `crf` state or straight to an interactive coder.
:::

:::{note} Checked against ten days of real runs
Four research passes read the transcripts and run files of 2026-10-17 to 27: costs, your
messages to running agents, the agents' own improvisations, and the messaging mechanisms of both
harnesses. Reports and scripts are in [evidence/](evidence/). Sections 3.2 to 3.5, 12 and 13
use their measurements.
:::

## 3. The parts

::::{grid} 1 2 4 4
:gutter: 2

:::{grid-item-card} 1 · Shared core
State as data, an event log, the `crf` state machine, role cards, schemas, the agent tag.
:::

:::{grid-item-card} 2 · Chief of Staff
The main session: conversation, backlog, grill, decisions. Steers runs through `crf`.
:::

:::{grid-item-card} 3 · crf-build
A thin workflow loop. Four CR slots; `crf step` says what comes next.
:::

:::{grid-item-card} 4 · Judge
A fresh LLM per event that needs judgment. Picks from a fixed menu of decisions.
:::

:::{grid-item-card} 5 · Steering
`crf` commands that change the state; every step reads it first.
:::

:::{grid-item-card} 6 · crf-land
Workflow after your merges: report, archive, cleanup script.
:::

:::{grid-item-card} 7 · Measurement
Cost per agent tag on both tools, with quality guardrails in every report.
:::

:::{grid-item-card} 8 · Recovery
Every step reads the state first, so relaunching a workflow resumes it.
:::
::::

### 3.1 Shared core

- **State as data.** Each CR's state lives as data, with an append-only `events.jsonl` per run.
  Tracking Markdown (`ORCHESTRATOR.md`, status tables, stack files) is generated by
  `crf render` and never edited by hand. This removes the stale hand-maintained status file
  seen in run 4.
- **`crf` state machine.** A Python script run with `uv run` and PEP 723 inline metadata.
  `crf step <cr>` records the last result, runs every mechanical step that follows, and returns
  only when the next step needs an LLM or the CR stops. It prints 10 to 30 lines and owns exit
  codes: the transcripts show coders masking them with `; echo exit $?`, so no long-suite
  failure ever had a non-zero exit.
- **Role cards and schemas.** Short neutral Markdown cards for the coder, the reviewer, the
  conflict fixer and the judge. JSON schemas for the reviewer's verdict, the coder's hand-over
  note and the judge's decision.
- **Agent tag.** Every agent carries `cr=<n> role=<role> round=<k> run=<id>` in the `label`
  that both workflow APIs accept. It replaces the regular-expression role guessing of the cost
  scripts.

### 3.2 Chief of Staff

What the main session keeps:

- **The conversation:** backlog triage, picking, the grill, scope, priorities, reports, the demo
  tour.
- **Opening and launching.** `crf open` creates the CR folders, briefs, state and worktrees, and
  replaces the ad hoc batch scripts. One `Workflow` call launches `crf-build`. Only the main
  session can do this: Claude Code withholds the `Workflow` tool from every subagent.
- **Steering.** Your wishes become `crf` commands, one short turn each (section 3.5).
- **Your decisions.** `crf wait --needs-you` runs as a background command. It exits when a CR
  needs a decision only you can take, or when the run ends. The harness then notifies the
  session, which tells you.

What it stops doing, measured on the main session of 2026-10-20 to 27:

| Orchestration work | Turns | Cost |
| --- | --- | --- |
| Reading or writing run state (`STATE`, `ORCHESTRATOR`, worktrees) | 341 | $22.46 |
| Reacting to agent notifications | 211 | $19.45 |
| git and gh status | 151 | $13.52 |
| Starting and restarting agents | 84 | $9.51 |
| Relaying messages (207 `SendMessage` calls) | 122 | $9.23 |
| Ad hoc scripts and monitoring | 142 | $10.51 |
| **Total: 43 % of the session's cost** | **1,051** | **$84.68** |

It also stepped in about 30 times for a failed child: 7 frozen orchestrators stopped, and one
API failure that took down 7 children and sat idle for 65 minutes until you typed again. In the
sketch a dead run ends the workflow, the session is notified, and a relaunch resumes it.

### 3.3 `crf-build`: the production loop

:::{figure} diagrams/crf-build-flow.svg
:label: fig-flow
:alt: Flow of one CR. Coder, then crf gate, then reviewer. FIX-REQUIRED loops back to the coder, three rounds at most. APPROVE goes to crf ship, crf ci wait and crf stack, with a judge on events that need judgment and a conflict fixer only on rebase conflicts. After the run: run ends, the user merges, crf wait in the background sees the merges, then crf-land.

One CR through `crf-build`, then `crf-land`.
:::

- **Four slots.** Four workers each pull the next CR with `crf next`, the factory's limit on
  open PRs. A CR you add during the run joins the queue; there is no fixed list to edit.
- **Round:** a fresh coder, then `crf gate`, then a reviewer that returns a schema-checked
  verdict. Rounds stop at three unless you, or the judge within a budget you set, grant more.
- **Hand-over note.** The coder ends each round with files touched, where the logic lives and
  pitfalls. A fresh coder per round is already the practice: only 10 of 116 round-1 coders
  were resumed. The note cuts the re-exploration of round-2 coders.
- **Ship and CI without an LLM.** `crf ship` commits explicit paths, pushes and opens the PR
  from the coder's `pr-body.md`. `crf ci wait` returns within ten minutes, the default ceiling
  of a foreground command on Claude Code, and the loop calls it again while CI runs.
- **Infrastructure failures.** Each CR gets a retry budget for CI hangs. One night, a CI step
  hung for 20 to 60 minutes on nearly every PR and one CR needed six attempts, so a single
  re-run is not enough. Repeated infrastructure failures across CRs stop the whole run once.
- **Baseline gate.** The run starts by checking the base branch and the tools once. In run 2,
  all 7 PRs went red from one stale tool; that becomes one stop, not seven blocked CRs.
- **Stack.** `crf stack` builds the chain from the order in the state, refuses base cycles,
  links it with `gh stack` and runs the heavy CI on top. When the top is red, `crf` bisects
  over stack prefixes and hands the result to the judge.
- **Conflicts.** Known files merge by rule: both sides of `CHANGELOG`, regenerated counts, IDs
  allocated at `crf open`. From 2026-10-22 to 27, 21 conflict fixers cost $3.22, nearly all
  "keep both". An LLM conflict fixer remains for the rest.
- **Shared machine.** Window tests queue on a lock in `crf`; a locked screen falls back to the
  heavy CI. Each CR gets its own `npm ci` instead of a shared `node_modules`.
- **Permission denials.** A denied step is recorded in the state with the exact command for
  you. The run goes on with the other CRs.

### 3.4 Judge

The orchestrators and drivers made real decisions that rules cannot make. The transcripts show
a handful of kinds: which CR caused a red stack, a flaky test or a real regression, one more
round or a stop, where to put a red PR in the stack. One night, the main session made six such
decisions in 49 turns for $5.25, and the stack was green at 06:24. Under "unknown means
blocked", that night would have waited for the morning.

- **When.** `crf step` returns `judge` for a red stack after bisect, a spent infrastructure
  budget, a round cap with a delegated budget left, or an unknown failure.
- **How.** A fresh agent with the judge card and the event's facts: about 50 lines from `crf`
  and log paths. It returns one decision from a fixed menu: retry, blame a CR and move it to the
  top, reorder, grant one round, mark a flake, block, or ask you.
- **Effect.** `crf` applies the decision and logs it with its reason. "Ask you" makes
  `crf wait --needs-you` exit, so the Chief of Staff tells you.
- **Cost.** An estimated 50 to 100k tokens per event on Sonnet, about $0.20 to $0.50. It
  replaces the judgment turns that cost about $32 in ten days, 14 % of the orchestration roles.
- **Scope.** The judge never edits code and never talks to you. Spec gaps stay with the coder,
  "is this failure mine" with the reviewer, scope and priorities with you.

With the rules of section 3.3 and the judge, about 6 to 8 CRs from 2026-10-22 to 27 would
still have stopped for you: 1 to 2 per run. The first sketch, with "unknown means blocked" and one
infrastructure re-run, would have stopped 20 to 25 CRs and 5 whole stacks.

### 3.5 Steering

Every `crf step` reads the state first, so a change takes effect at the next step: after the
running coder or reviewer finishes, usually minutes. Messages to running agents do worse
today. An agent reads a message only at its next tool round, and an orchestrator waiting on its
drivers has none.

| Your messages to running agents, 2026-10-17 to 27 | Count |
| --- | --- |
| Sent by the main session to orchestrators | 89 |
| of which never delivered | 16 |
| of which delivered more than 30 minutes late (worst: 8 h 05 min) | 23 |
| Sent straight to drivers, all delivered, median 2 minutes | 14 |

What those messages did, and where each kind goes in the sketch:

| What you asked for | Messages | In the sketch |
| --- | --- | --- |
| Merge done: land, rebase the rest | 21 | the workflow, through merge detection |
| Change a CR's scope in flight | 19 | `crf note <cr>`, read by the next round |
| Change a process rule mid-run | 19 | the policy card and `rules.md`, read at every step |
| Add, remove, reprioritise | 15 | `crf add --after`, `crf cancel`, `crf order` |
| Restart after a stall or rate limit | 11 | the workflow: a relaunch resumes |
| Stack shape: reorder, add on top | 11 | `crf stack order`, checked for base cycles |
| Grant extra rounds | 9 | `crf grant <cr> <n>`, or a budget for the judge |
| Ask where things stand | 8 | `crf status`, in the Chief of Staff |
| CI or infrastructure decision | 5 | the judge |
| Ownership and coordination | 5 | `crf hold` and `crf release` |
| Unblock a denied step | 4 | the command recorded in the state |
| Pause, you need the machine | 3 | `crf pause`, `crf slots <n>` |

"A driver built the stack dynamically" holds for the execution: commits, bases and CI runs. The
order and its reasons came from the main session and from files it had just updated. 66 of 103
steering messages pointed to such a file. No case was found where your flexibility depended on
something only an orchestrator or a driver knew.

**Interactive lane.** Three to five times in ten days, you redirected a coder in the middle of
a round while it kept its knowledge of the code. For CR 084 you changed the design three times
from screenshots, and each change reached the same coder within minutes. A workflow agent
cannot take messages, so such a CR leaves the workflow: `crf hold <cr> --interactive`. The
Chief of Staff starts its coder as a background subagent you talk to directly. `crf release`
hands the CR back for review, ship and CI.

### 3.6 `crf-land`: after the merges

- Writes the report with every link, archives the CRs, updates the state.
- Writes the cleanup script for worktrees and branches. **You run it**, since the
  auto-mode classifier denies those deletions to agents.
- Two workflows instead of one: Claude Code workflows take no input mid-run. On Copilot,
  `ctx.pause("land")` would allow one workflow, but two keep both harnesses identical.

### 3.7 Measurement

- One row per agent turn: run, CR, role, round, tool, model, timestamp, gap since the previous
  turn, input, cache read, cache write, output, a rebuild flag and the estimated cost.
- Read by [copilot-session-usage](https://github.com/gsemet/copilot-session-usage), extended
  with a Claude Code reader, grouped by agent tag.
- Every report shows the quality guardrails: rounds used, reviewer verdicts, CI failures and
  CRs reopened after merge. A cost cut that adds rounds is not a gain.
- It also counts judge decisions, the ones you reversed, steering commands, and the CRs that
  stopped for you.

### 3.8 Recovery

Each step reads the CR's state before acting and skips what is already done. Relaunching the
same workflow therefore resumes it, on both harnesses and in a new session. Copilot's
`resume(runId)` becomes a convenience, not a dependency. The API error that killed an
orchestrator in run 4 then costs one relaunch.

## 4. Where `/loop` and the CLIs run

| Moment | Mechanism | Claude Code | Copilot CLI |
| --- | --- | --- | --- |
| Open CRs | `crf open` | main session | main session |
| Gates, commit, PR, CI wait, stack | `crf step` | a Haiku agent runs one command and returns its JSON | `ctx.step` runs it, no LLM |
| Steer a run | `crf note`, `hold`, `grant`, `order`… | main session, one short turn | main session, one short turn |
| Wait for a decision only you can take | `crf wait --needs-you` | background Bash; notification on exit | background shell; notification on exit |
| Follow a run | end-of-run notification, `/workflows` | native | native |
| Wait for your merges | `crf wait --merged`, then launch `crf-land` | background Bash, or `/loop 30m` | background shell, or `/loop 30m` |
| Night batch, session closed | cron | `claude -p` allowed to run `Workflow(crf-build)` | `copilot --experimental workflow run crf-build` |
| Keep the cache warm | — | not needed: the main session waits outside the LLM | no long TTL yet, see copilot-cli#5220 |
| Regenerate tracking files | `crf render` | inside `crf step` | inside `crf step` |

:::{tip} Waiting costs nothing until something happens
Claude Code notifies a session when one of its background commands ends, and a local
interactive session puts no time limit on them. The main session therefore waits on
`crf wait` instead of ticking: one turn per event that matters. `/loop` stays the fallback for
unattended sessions, where background commands have a time limit.
:::

## 5. One factory, two harnesses

:::{figure} diagrams/portable-core.svg
:label: fig-core
:alt: Two adapter cards, Claude Code and Copilot CLI, above a shared JavaScript workflow body, above four core parts: crf CLI, CR state and event log, role cards and schemas, measurement.

The workflow body and `crf` are written once; each harness gets a thin adapter.
:::

The logic lives in `crf`, in Python, with tests. The workflow body is a short loop that asks
`crf step` what comes next, so the two adapters stay small. A Claude Code workflow cannot load
modules, so `crf` copies the body into each adapter file.

```{code-block} javascript
:caption: Sketch of the shared body. Names are illustrative, not an API.

// io = { agent, parallel, phase, sh } is provided by each adapter.
async function crfBuild(io, run) {
  io.phase('Build')
  const slot = async n => {
    for (;;) {
      const cr = await io.sh(`uv run crf next ${run.id} --slot ${n}`)
      if (cr.none) return
      await buildOne(io, run, cr.id)
    }
  }
  return io.parallel([1, 2, 3, 4].map(n => () => slot(n)))
}

// crf step records the last result, applies notes, holds and grants,
// runs gate, ship, CI wait and stack, and returns only when an LLM is needed.
async function buildOne(io, run, id) {
  let result = null
  for (;;) {
    const next = await io.sh(`uv run crf step ${id}`, result)
    if (next.stop) return next            // ready, blocked, held, cancelled
    result = await io.agent(next.prompt, {
      label: `run=${run.id} cr=${id} round=${next.round} role=${next.role}`,
      schema: next.schema,                // verdict, hand-over note or decision
    })
  }
}
```

```{list-table} What each adapter supplies
:header-rows: 1
:widths: 26 37 37

* - Piece
  - Claude Code
  - Copilot CLI / SDK
* - File
  - `.claude/workflows/crf-build.js`
  - `.github/extensions/crf-build/extension.mjs`
* - `sh(cmd, input)`
  - `agent()` on Haiku with a one-line prompt and a schema for the JSON result; Haiku is required, Sonnet runners would cost $50–66 a week
  - `ctx.step(key, …)` running the command, journaled
* - Concurrency
  - four slots in the body; runtime default is 16 agents
  - same in the body; `maxConcurrentSubagents` as a backstop
* - Budget
  - none in the runtime; `crf` caps rounds, retries and judge calls
  - `maxAiCredits` on top of the same caps
* - Interactive lane
  - a background subagent of the main session; `SendMessage` or its transcript
  - a background agent; `write_agent` or `/tasks`
* - Launch headless
  - `claude -p`, permission rule `Workflow(crf-build)`
  - `copilot --experimental workflow run crf-build`, tools granted with `--allow-tool`
```

## 6. The `crf` CLI

All names are working names.

| Command | Does | Replaces |
| --- | --- | --- |
| `crf open <items…>` | CR folders, briefs, state, worktrees, IDs, table rows | ad hoc batch scripts |
| `crf next <run>` | The next CR for a free slot, in the order of the state | a fixed CR list |
| `crf step <cr>` | Records a result, runs the mechanical steps, returns the next LLM step | driver turns |
| `crf gate`, `ship`, `ci wait`, `stack` | The steps `crf step` runs; callable alone for debugging | driver and stack driver turns |
| `crf wait [--needs-you\|--merged]` | Blocks until a CR needs you, the run ends, or PRs merge | notifications and polling in the main session |
| `crf status [--notes]` | A few lines per CR | raw git and gh output in an LLM |
| `crf set`, `render`, `lint` | State edits with an event; generated Markdown; checks | hand edits of `STATE.md` |
| `crf land` | Report, archive, cleanup script for you | orchestrator landing turns |
| `crf measure <run>` | Cost per tag and guardrails, through copilot-session-usage | `analyze.py`, `roles.py` |

Steering commands, all read by the next `crf step`:

| Command | Effect |
| --- | --- |
| `crf add <items…> [--after <cr>\|--top]` | Opens CRs and queues them in the running batch |
| `crf cancel <cr>`, `crf order <cr…>` | Drops a CR; sets the queue order |
| `crf note <cr\|--all> <text>` | Added to the next coder's or reviewer's prompt |
| `crf hold <cr> [--interactive]`, `crf release <cr>` | Takes a CR out of the workflow, for you or an interactive coder |
| `crf grant <cr> <rounds>`, `crf policy <key>=<value>` | Extra rounds; the judge's budget and rules |
| `crf stack order <cr…>` | New stack order, refused if it creates a base cycle |
| `crf pause`, `crf resume`, `crf slots <n>` | Frees the machine; changes the number of active CRs |

Forge commands run with `GH_PAGER=cat GH_PROMPT_DISABLED=1` or `GLAB_PAGER=cat
GLAB_NO_PROMPT=true`, so no command ever waits for input.

## 7. What changes in the skill

| Lifecycle step | Owner today | Owner in the sketch |
| --- | --- | --- |
| 1 Pick, 2 Grill | main session | Chief of Staff |
| 3 Open, 4 Brief | main session with ad hoc scripts | Chief of Staff with `crf open` |
| 5 Code | coder | coder, fresh each round, hand-over note |
| 6 Review | reviewer | reviewer, schema-checked verdict |
| 7 Commit, 8 PR | driver | `crf step` |
| 9 CI | driver | `crf step`, new round on product failure |
| Decisions across CRs | orchestrator, often the main session | judge; you, through the Chief of Staff |
| Steering during a run | messages relayed to an orchestrator | `crf` commands read at every step |
| 10 Notify | driver | `crf wait`: end of run, or a CR that needs you |
| 11 Land | orchestrator | `crf-land` and your cleanup script |

The skill text shrinks to what an LLM still does. `SKILL.md` keeps the entry-point table and
the hard rules. `parallel.md` and `stacked-prs.md` become short pages about launching, steering
and reading runs. The forge pages move inside `crf`, so no agent loads them any more.

## 8. Settings

```{code-block} json
:caption: Claude Code, project settings for runs

{
  "permissions": {
    "allow": ["Workflow(crf-build)", "Workflow(crf-land)"]
  }
}
```

```{code-block} bash
:caption: Launching on each harness

# Claude Code: a bounded main session
claude --autocompact 100000

# Copilot CLI: experimental mode is needed for workflows and /every
copilot --experimental
copilot --experimental workflow run crf-build --args @run.json --output-format json
```

`--experimental` is only needed where the `experimental` setting is not already on, such as a
CI runner.

## 9. Measuring each lever

Change one lever at a time, measure, keep it only if the guardrails hold.

| Lever | Main metric | Guardrail |
| --- | --- | --- |
| Workflow and judge instead of orchestrator and drivers | orchestration share of the subtree cost | rounds per CR; judge decisions you reversed |
| Chief of Staff main session | share of main-session cost on orchestration, 43 % today | CRs that waited for you; your "where are we" questions |
| Long suites and CI waits moved into `crf` | cost of cache rebuilds | CI failures caught |
| Hand-over note | coder cost before the first edit in round 2 | reviewer verdicts in round 1 |
| Smaller models for some roles | cost per CR | rounds per CR, reopened CRs |

Two ways to measure, to be chosen: replaying six to eight archived CRs from their base commit
(precise, paid) or observing real runs (free, noisy).

## 10. Risks

:::{warning} What could break the sketch
- **Preview APIs.** Copilot dynamic workflows are in public preview and marked experimental.
  The Copilot SDK v2 will break APIs. Keep the adapters thin.
- **No shell in Claude scripts.** Every `crf` call costs one small agent on Claude Code. It must
  run on Haiku: on Sonnet the runners would eat a third of the main saving.
- **Judge drift.** A judge that improvises outside its menu brings the driver back. Its
  decisions are logged with a reason, and the ones you reverse are counted.
- **No long cache on Copilot.** Any LLM wait over five minutes rebuilds the cache there.
- **VS Code harness gaps.** Open issues show custom agents losing their tools as subagents and
  model choices being ignored. Copilot CLI is the safer target for now.
- **Headless permissions.** `copilot workflow run` shows no prompt; requests not granted in
  advance are denied. Denials must surface in the state, never be worked around.
:::

## 11. Open questions

Each question carries a recommended answer.

1. **Where does the CR state live?** Recommended: the front matter of `STATE.md`, validated by
   okf-schema and shown by the Studio, rather than separate JSON files.
2. **Where does `crf` live?** Recommended: a script in the skill folder first; a package only
   if it grows.
3. **Which model for the judge?** Recommended: Sonnet, with the reversed decisions as the
   guardrail; Opus only if reversals show it is needed.
4. **Where does measurement live?** Recommended: a Claude Code reader added to
   copilot-session-usage, so both tools share one row format.
5. **How does Claude Code run `crf`?** Recommended: a Haiku agent per `crf step`; measure it
   against a background shell in the main session.
6. **How does nesting count inside a Claude workflow?** A subagent may spawn its own subagents
   down to three layers below the main conversation. The docs do not say where workflow agents
   sit in that count. A spike should check that a coder can still delegate a search.
7. **What must a Copilot spike confirm?** That a workflow step can run a child process, that
   workflow agents see the repository's custom agents, and how credits map to labels.
8. **A one-hour TTL for subagents until the levers land?** Recommended: try it now and measure.
   Today it would save about $28 over the ten days, because subagents rebuild $221 of cache. It
   must be switched off once waits leave the LLMs, where it would add about $87 a week.

## 12. Expected saving

The estimate uses the transcripts of 2026-10-17 to 27, measured in
[evidence/01-costs.md](evidence/01-costs.md). The first activity is on 10-20, so the window holds
7.6 active days: **$1,705 at API rates, about $1,573 a week**, 947 agents. It assumes the same
activity, with every orchestrated batch run as a workflow, requirements batches included.

:::{figure} diagrams/savings-waterfall.svg
:label: fig-savings
:alt: Waterfall chart. Orchestrators and drivers become code 160 to 184 dollars, no LLM waits in coder rounds 40 to 57, shorter coder contexts 15 to 40, Chief of Staff main session 65 to 105, minus overlap 10 to 30, minus added costs 12 to 63, giving a net saving of 185 to 365 dollars a week, 12 to 23 percent.

From gross levers to the net weekly saving.
:::

```{list-table} Gross saving per lever
:header-rows: 1
:widths: 22 32 30 16

* - Lever
  - Measured base, 7.6 days
  - What the sketch removes
  - Per week
* - Orchestrators and drivers become code
  - Own cost of orchestrators, drivers, stack drivers, task drivers and integrators: $231, of which $91 is cache rebuilds
  - 75–86 %: 86 % of their turn cost is mechanical. The rest is judgment, which the judge now pays for
  - **$160–184**
* - No LLM waits in coder rounds
  - Rebuilds after long suites $42, CI polls $10, background waits $5
  - 70–100 %: a UI fix must still reproduce the bug in the coder
  - **$40–57**
* - Shorter coder contexts
  - Coder shell reads $163, mostly source code; test and CI output already averages 400–450 tokens
  - Targeted reads, 25–50 % of $46; a hand-over note for round-2 coders
  - **$15–40**
* - Chief of Staff main session
  - Orchestration turns in the main sessions: $91; 43 % of the busiest one
  - 60–80 % of them; compaction at 100k tokens on the rest, 10–23 %
  - **$65–105**
```

```{list-table} From gross to net
:header-rows: 1
:widths: 50 30 20

* - Item
  - Basis
  - Per week
* - Gross saving
  - sum of the four levers
  - $280–386
* - Overlap between levers
  - the levers touch different roles, except fewer rebuilds; 3–8 %
  - −$10–30
* - Haiku agents that run `crf` on Claude Code
  - 8 to 10 calls per CR, about 94 CRs a week, $0.005–0.01 each
  - −$4–10
* - Waiting and status in the Chief of Staff
  - one short turn per event on a bounded context
  - −$3–10
* - Extra rounds
  - 13 to 67 long-suite or CI failures that a coder fixed itself become a fresh coder, $0.42–0.69 each
  - −$5–43
* - **Net saving**
  - **12 to 23 % of the week**
  - **$185–365**
```

The judge needs no line of its own. Lever 1 removes at most 86 % of the orchestration roles'
cost, which leaves about $30 a week for judgment. At $0.20 to $0.50 per event, that pays for
60 to 150 decisions a week. That should cover the events left after the rules of section 3.3;
the first runs will measure it.

**Per CR.** In runs 1 to 3, a CR cost **$3.72 to $6.93** all-in, main-session orchestration
included. The sketch brings it to **$2.27 to $4.99, an 18 to 39 % cut**. Run 2 shows the floor:
its orchestration was already lean, and coders dominate. Per-CR cost is driven by a few CRs, such
as one at $21 after six rounds, so round caps and stable specifications matter as much as
orchestration.

**Factory only.** The CR factory, with the main session's orchestration, was about 42 % of the
window. Its net saving is about **$117–242 a week**.

:::{warning} Two levers deliberately left out
- **A one-hour cache TTL for all agents.** It would save about $28 over the ten days as things
  are, and add about $87 a week once waits leave the LLMs. It is an open question as a
  stop-gap (section 11), not a lever of the sketch.
- **Model changes.** Sonnet instead of Opus for coders could save up to 30 % of the Opus coder
  cost. It changes quality, so it needs its own measurement on about ten CRs. It is not counted
  here.
:::

:::{note} What the data changed
The first estimate said $140–300 a week, 10–22 %. The net share holds; its make-up does not.
The Chief of Staff lever is three times larger than first counted, because the main session was
a hidden orchestrator. Shorter contexts give half as much, because command output was already
short and the shell reads are source code. Sessions ran on a subscription, so these dollars are
API-rate equivalents: the saving buys more work within the same plan limits. Building `crf`, the
judge and the two workflows takes developer time, and a replay bench of 8 CRs × 2 variants × 2
tools costs roughly $65–190.
:::

## 13. What the sketch gives up

Measured against what the agents and you actually did from 2026-10-17 to 27, with the evidence
in [02-dynamics.md](evidence/02-dynamics.md) and [03-judgment.md](evidence/03-judgment.md).

| Capability today | In the sketch | What the data says |
| --- | --- | --- |
| Talking to a running orchestrator | `crf` commands, read at the next step | Gained, not lost: 16 of 89 messages to orchestrators never arrived and 23 came over 30 minutes late |
| A driver builds the stack dynamically | `crf stack` from the state order; `crf stack order`; the judge places a red PR | Kept: the order and its reasons came from you and from files; one driver reorder created a base cycle |
| Changing the plan mid-run | A queue fed by `crf add`, `cancel`, `order`, `hold`; rules read at every step | Kept for all twelve kinds of messages seen; only the script itself cannot change mid-run |
| Redirecting a coder mid-round, keeping its context | The interactive lane, chosen per CR | Partly lost: you must pick the lane before the round; 3 to 5 cases in ten days |
| Orchestrators and drivers improvising on surprises | Rules in `crf`, then the judge's fixed menu | Kept: no driver decision was found that rules, the coder, the reviewer or a judge could not make |
| Free-form decisions outside any menu | "Ask you": the CR waits for the Chief of Staff | Lost at night: about 1 to 2 CRs per run wait for the morning |
| "Do something else, the factory goes on" | Unchanged, and the main session is no longer busy relaying | Gained: 43 % of the main session's cost was orchestration |
| An agent asks you a question during a run | The judge's "ask you", through `crf wait --needs-you` | Kept, one turn per question |
| An orchestrator subagent runs a whole batch alone | Only the main session can launch a workflow on Claude Code | One `Workflow` call per batch |
| The process changes by editing a prose guideline | Rules that need judgment stay in cards; mechanics change in Python, with tests | A cost: some changes need code |
| The orchestrator transcript tells why | Events in the log, each with a reason; judge decisions included | Kept, and searchable |

**What is really lost:**

- **Mid-round redirection** of a coder that you did not put in the interactive lane. It waits
  for the end of its round, then reads your note.
- **Night improvisation beyond the menu.** A case the judge cannot place waits for you.
- **Editing the factory's mechanics in prose.** It now takes a change to `crf`.
- **VS Code's own harness.** Dynamic workflows are not documented there yet; the sketch targets
  Claude Code and Copilot CLI.
