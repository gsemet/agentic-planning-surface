# Design report: the Foreman workflow under test (series 08, run A)

Date: 2026-10-29, written at 16:12 CET while the run is still going.
Scope: the solution **actually running** in series 08 run A: a Foreman dynamic workflow that
implements Jira NESTOR-36450 (agpkg `install` performance) on the real agpkg repository. It
describes what was built, how it behaves, what it costs so far, and where it departs from the
target design of [04-handoff.md](./04-handoff.md) section 6. Final numbers go to
`tests/08-hybrid-real-repo/README.md` once the run ends.

---

## 1. Context

- **Change:** NESTOR-36450. A FullCycle plan already existed in agpkg
  (`.agents/changes/requests/performance-improvements/`): `03-specification.md`,
  `05-task-00-READBEFORE.md` and 12 task files (`05-task-01` … `05-task-12`). The plan was
  written against an **older agpkg version**, so some paths, symbols and assumptions are
  stale.
- **Series 08 plan:** two parallel attempts on the same plan, each in its own worktree:
  - **Run A, Foreman** (this report): dynamic workflow, 12 tasks stacked as pseudo-CRs, escalation ladder in code;
  - **Run B, FullCycle**: Compendium skills `04-implementation` then `05-finalization` in one
    agent session. **Stopped** at $4.33 after 2 commits, because its orchestrator passed
    `model: "gpt-6.1-sol"` with `general-purpose` agents for routine subtasks (no fixed-model
    custom agents). Lab: `agpkg-labs/nestor-36450/fullcycle`, session
    `eda293fd-978d-4ccf-9d00-f6136eba07fc`.
- **Vocabulary:** NESTOR-36450 is **one change request (CR) split into 12 tasks**. To test
  the dynamic Foreman, the kit treats each task as a stacked pseudo-CR with ids `CR-01` to
  `CR-12` (in `inbox.json`, `status.json`, `run.log` and marker branches). In this report,
  "task" means one of these units; the ids are kept as they appear in the run files.
- **Harness:** Copilot CLI 1.0.105 (`copilot --experimental … workflow run`), launched
  headless from the Chief of Staff (CoS) session in the VS Code Agents host.

## 2. Architecture

```text
User ⇄ CoS chat ──edits──▶ <lab>/inbox.json ◀── re-read before each round ── foreman workflow
          ▲                                                                   │ (extension.mjs,
          └──── reads ── <lab>/status.json, run.log, git log ◀── writes ──────┤  no LLM)
                                                                              │
                         one stack worktree <lab>/wt ◀── commits ── coder (Luna)
                                                     ◀── reviews ── inspector (Luna, JSON)
                                                     ◀── decides ── judge (Sol, JSON, round 2)
                                                                              │
                                     Publish: mr.md (Luna) → git push → glab mr create --draft
```

| Role (handoff names) | Implemented as | Model |
|----------------------|----------------|-------|
| Chief of Staff | the user's chat session; prepares the lab, launches, reports | user's choice |
| Foreman | `foreman` dynamic workflow, `extension.mjs` (121 lines), no LLM | none |
| Driver | the per-CR loop in code (`deliver`), plus a Sol **judge** call at round 2 | judge: `gpt-6.1-sol` |
| Coder | custom agent `coder` (`.github/agents/coder.agent.md`) | `gpt-5.6-luna` |
| Inspector | custom agent `inspector`, JSON output `{blocking[], minor[]}` | `gpt-5.6-luna` |
| Fallback Coder | same `coder` agent with `model: "gpt-6.1-sol"` override after a judge `escalate` | `gpt-6.1-sol` |
| Interactive Driver | `needs-driver` tasks left for the CoS to hand to a session | not started yet |
| Stack role | single stacked branch, one marker branch per task | none |

## 3. Components

### 3.1 Lab layout (`kit/setup.sh`, 23 lines)

`setup.sh <repo> <labs-root> <cr-folder>` builds, for run A, under
`agpkg-labs/nestor-36450/foreman/`:

| Path | Content |
|------|---------|
| `launcher/` | detached worktree on `origin/master`; holds the **untracked** `.github/extensions/foreman/extension.mjs` and `.github/agents/{coder,inspector}.agent.md`. The workflow runs from here so the kit never enters the CR branch. |
| `wt/` | the stack worktree, branch `dev/gsemet-NESTOR-36450-foreman` from `origin/master` |
| `cr/` | a copy of the FullCycle plan folder, outside the repository (read-only for agents) |
| `inbox.json` | `{crs: [{id, file}], changes: [], cancel: []}`, one CR per task file 01–12 |
| `status.json`, `run.log` | written by the workflow |
| `cli.out`, `result.json`, `started.txt` | CLI output, final workflow result, start and end times |

### 3.2 Workflow (`kit/extension.mjs`)

- `meta.limits`: `maxConcurrentSubagents: 1`, `timeoutSeconds: 8 h`, `maxAiCredits: 10000`
  ($100 cap, a safety net, not a budget).
- **Build phase:** loop `inbox().crs.find(not done)`. The inbox is re-read before each CR, so
  `add` (append) and `reorder` (edit array order) take effect at the next task boundary.
- **`deliver(c)`** per task, at most 4 rounds:
  1. stop if `c.id` is in `inbox.cancel`;
  2. Coder call with the brief, the user changes for this CR from `inbox.changes`, and the
     previous blocking findings; unique label `CR-n:coder:rN` (avoids memoization);
  3. Inspector call on `base..HEAD` with the JSON schema;
  4. no blocking findings → accept;
  5. after round 2, if still blocking: Sol judge → `accept` (stop, findings waived), `escalate`
     (later rounds use the Coder with `model: "gpt-6.1-sol"`), or `fix` (continue on Luna);
  6. after round 4 with findings: `needs-driver`.
  At the end of every CR: marker branch `nestor-36450-foreman-cr-nn` on `HEAD`, final state
  and open findings saved.
- **Stale-plan handling:** the brief tells the Coder that the plan predates the code: check
  every path, symbol and anchor, adapt, and skip obsolete steps with a note in the commit body.
- **Publish phase:** a Luna call writes `<lab>/mr.md` (user impact, overview, one bullet per
  commit, `Closes NESTOR-36450`, open findings), then the code pushes the branch and runs
  `glab mr create --draft`. The MR URL goes into `status.json`.
- **Status:** `save()` writes `status.json` (full state per task) and appends to `run.log` at every
  transition: `coding`, `inspecting`, `reviewed`, judge decision, final state.

### 3.3 Agents

- **`coder`** (tools: view, edit, create, bash, grep, glob): `cd` into the worktree, read
  `AGENTS.md`, follow project rules, run focused tests and the gates the task requires, never
  claim an unrun gate passed, commit with Conventional Commits, never push or rewrite older
  commits, reply in at most 10 lines.
- **`inspector`** (tools: view, bash, grep, glob): read-only review of the commit range against
  the task and read-before files; may run focused `uv run pytest`; only defects worth another
  round are `blocking`; replies with JSON only.

### 3.4 Launch

```bash
L=<labs>/nestor-36450/foreman; cd $L/launcher
GITHUB_COPILOT_PROMPT_MODE_EXTENSIONS=true copilot --experimental --allow-all-tools \
  --add-dir $L --add-dir <agpkg repo> --add-dir $HOME/.cache/uv --add-dir /tmp --add-dir /private/tmp \
  workflow run foreman --args "{\"lab\":\"$L\"}" --result-file $L/result.json > $L/cli.out 2>&1
```

The repository itself needs `--add-dir` because worktrees share its `.git` directory; the uv
cache is needed for `uv run`.

## 4. Behaviour observed so far (16:11 CET, 2 h 08 after start)

| Task id | Task | Rounds | Judge | State |
|----|------|-------:|-------|-------|
| CR-01 | requirements and ADR | 1 | – | done |
| CR-02 | trusted streaming cache | 4 | fix | **needs-driver** (1 blocking) |
| CR-03 | cache locking and verification | 3 | fix | done |
| CR-04 | install report contract | 1 | – | done |
| CR-05 | install operations and timings | 4 | fix | **needs-driver** (3 blocking) |
| CR-06 | update duplicate diagnostics | 3 | fix | done |
| CR-07 | (task 07) | 2 | – | done |
| CR-08 | (task 08, parallel materialization and progress) | 4 | fix | **needs-driver** (2 blocking) |
| CR-09 | CLI and Zen parity | 2 | – | done |
| CR-10 | integration campaigns | 2 (running) | – | coding round 2 after 4 blocking |
| CR-11, CR-12 | documentation and release; final validation and FOD | – | – | queued |

- 25 commits on the stack branch so far; average about 13 minutes per task.
- Open findings on the `needs-driver` tasks are real defects, not nits. Examples: CR-02 still
  requires the remote size (`size_in_remote()` returns `int`) and fails when a remote does not
  advertise it; CR-05 does not normalize SHA-256 in the acquisition key and loses timings on
  failure; CR-08 lets duplicate operations push the progress bar past its total.
- The Coder adapted the stale plan as instructed (for example CR-09: "earlier API/core
  functionality was already present and left unchanged"), and reports gate results
  (`just checks`, `just tests-coverage`).
- No steering was used in this run: `inbox.changes` and `inbox.cancel` stayed empty.

## 5. Cost so far

Measured with `evidence/scripts/session_cost.py` on the run's session
`6800fc59-2823-4eea-8b2a-064cd3f016e8` at 16:00 (CR-01 to CR-08 complete, CR-09 in review):

| Role | Agent runs | Model calls | USD | Share |
|------|-----------:|------------:|----:|------:|
| Coder (Luna) | 23 | 821 | 1.46 | 69 % |
| Inspector (Luna) | 23 | 234 | 0.46 | 22 % |
| Judge (Sol) | 5 | 18 | 0.20 | 9 % |
| Foreman (workflow code) | – | 0 | 0.00 | 0 % |
| **Total** | | | **2.12** | |

- About **$0.24 per task** (9 tasks touched), against $0.006 per toy CR in series 07 and $0.12
  in series 06b (those were single small CRs, closer in size to one task here).
  Real tasks moved the bill entirely to Coder and Inspector work; orchestration is
  still free.
- One judge call cost $0.09 (CR-02, 4 calls with a cold cache); the others cost about $0.02.
- Not counted: the CoS turns spent preparing, launching and checking the run.
- Projection at the end of the run (3 tasks plus publish): about $2.8–3.0. For comparison, run B
  (FullCycle) spent $4.33 for 2 commits before it was stopped.

## 6. Departures from the target design (handoff section 6)

| Target | Run A | Why or effect |
|--------|-------|---------------|
| One worktree per CR, CRs in parallel | one CR: its 12 tasks stacked in one worktree, `maxConcurrentSubagents: 1` | the tasks depend on each other; stacking avoids rebase work but serializes the run |
| Ladder: judge `escalate` → Sol Coder | up to task 09 the judge returned `fix` 5 times out of 5, so the Sol Coder was never used; it escalated later on CR-10 (then accepted on Sol) and CR-12 | on `fix`, rounds 3–4 stay on Luna, and 3 tasks ended `needs-driver`; a `fix` decision should also escalate (see 7.1) |
| `needs-driver` → interactive Driver session | not started yet; the tasks stay open | hand-off planned after the run |
| `reopen` operation, stacked PRs | not implemented; one draft MR for the whole stack | the Jira issue maps to one MR |
| Detached launch | launched in an **attached** async shell | the CoS session stayed busy for the whole run; the user's messages queued (see 7.4) |

## 7. Issues and proposed changes

1. **Escalation never triggers.** The Sol judge consistently answers `fix` ("bounded changes")
   and the loop keeps Luna. Proposal: after round 2, `fix` and `escalate` both switch the Coder to
   Sol; the judge only decides `accept` versus `continue`. This is the AutoCycle rule (fallback
   Coder from the third rework, or as soon as a finding repeats).
2. **Stack contamination.** A `needs-driver` task keeps its commits on the stack, and later
   tasks build on top of known defects (CR-02 under CR-03 to CR-12). Options: stop the stack at
   the first `needs-driver`, or record the open findings in the next tasks' briefs so the Coder
   knows about them.
3. **No end-of-development gate in code.** Gates are run by each Coder and checked by the
   Inspector, but nothing runs the project preflight (`just preflight`) on the final stack before
   publishing. Proposal: a Coder "fix-gates" step between Build and Publish.
4. **The launch blocked the CoS.** An attached shell cannot be detached later. Long runs must
   start with the bash tool `mode: "async"` and `detach: true`; this rule is now written in the
   AutoCycle Chief of Staff skill.
5. **Commit history not finalized.** The MR will carry 25+ Coder commits without squash or DCO
   sign-off, unlike FullCycle `06-finalization`. Acceptable for a draft MR; the user squashes on
   take-over.
6. **Telemetry size.** The single run session holds every subagent: `events.jsonl` is 43 MB at
   CR-09, and reading it synchronously blocks the CoS. Compute costs in a detached job.

## 8. Relation to AutoCycle

The AutoCycle skills (`compendium-fullcycle:chief-of-staff` and `autocycle-driver`) built in
parallel take the opposite trade-off: a Sol Driver **session** per CR, running the FullCycle
stages with fixed-model custom agents (`autocycle-planner` Sol, `autocycle-coder` Luna,
`autocycle-coder-fallback` Sol, `autocycle-inspector` Luna), a JSON state per CR with a
reproducible Markdown report, autonomous decisions logged, and squash plus sign-off before a
draft MR. It adds orchestration cost (the Driver session) that this workflow does not pay, in
exchange for live steering, replanning and FullCycle-compliant delivery. Run A's numbers give
the baseline that AutoCycle must be compared against.

## 9. Next steps

1. Let the run finish (estimated 17:00–17:15 CET): CR-10 to CR-12, `mr.md`, push, draft MR.
2. Measure the final cost (detached job), archive `events.jsonl`, `inbox.json`,
   `status.json`, `result.json`, `run.log` and `mr.md` into `tests/08-hybrid-real-repo/results/`.
3. Hand CR-02, CR-05 and CR-08 to an interactive Driver (check E2), or test proposal 7.1 by
   rerunning them with the Sol Coder.
4. Update the reports listed in handoff section 8 and append to its log.
