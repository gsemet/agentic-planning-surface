# Handoff: from series 01–07 to series 08 (hybrid factory on a real project)

Date: 2026-10-29. Written by the Chief of Staff session that ran series 01–07.
Audience: a **fresh agent session with no prior context**, working in **another project**, that
runs series 08 as real development work. It must report its findings back into this folder so
the original session (or any later one) can resume from the files alone.

Read this file first, then [03-comparison-report.md](./03-comparison-report.md), then
[tests/07-dynamic-workflow/README.md](./tests/07-dynamic-workflow/README.md). Everything else is
background.

---

## 1. Mission in one paragraph

Build a **change-request (CR) factory** on GitHub Copilot (CLI 1.0.105 in the VS Code Agents host)
in which **token cost is the absolute priority**. Billing has been token-based since June 2026;
there are no premium requests any more, and the budget is tight. The user steers the work live:
they review a task in progress, change a running task, add tasks, reorder them, and fix an
already open PR. The factory must absorb these interventions cheaply. Series 01–07 showed that
the cheapest working engine is a **dynamic workflow** (code) rather than LLM sessions. Series 08
must prove the recommended **hybrid** on real CRs in a real repository.

## 2. Roles (user-defined names, keep them)

| Role | What it is | Implemented as (recommended) |
|------|-----------|------------------------------|
| **Chief of Staff (CoS)** | The user's only conversation. The user grills it, hesitates, changes direction. | The main chat session |
| **Foreman** | Translates instructions, schedules CRs, aims for the best output at the lowest cost, ends when all work is done. | **Dynamic workflow code** (`extension.mjs`), no LLM |
| **Driver** | Hired per CR, works in isolation (own worktree), delivers at the highest quality for the lowest cost, decides if an Inspector finding is worth another Coder round. | **Rule in workflow code**, plus an LLM judge only on escalation, plus an interactive session only as a last resort |
| **Coder** | Implements the CR. | Custom agent `coder` on `gpt-5.6-luna` |
| **Inspector** | Same CR, hyper-critical review of the output. | Custom agent `inspector` on `gpt-5.6-luna`, JSON-schema output |
| **Stack role** (optional) | Manages stacked PRs/MRs ([GitHub stacked PRs](https://docs.github.com/fr/pull-requests/get-started/about-stacked-prs), [glab stack](https://docs.gitlab.com/cli/stack/)). | Not tested yet; a separate step or session hired by the Foreman |

## 3. User constraints (non-negotiable)

- Talk to the user in **French**. Everything written in files is in **English**.
- Run Python **always** with `uv run` (never `python` / `python3`), including helper scripts.
- **Never commit** in the design repository (`agentic-planning-surface`). Commit in the target
  project only per that project's rules.
- **No complex scripts.** The user rejected heavy orchestration scripts; keep kits small and
  readable (the 07 workflow is about 70 lines).
- Sessions and runs must **end themselves cleanly**; the user must not have to close anything.
- If sessions are used, the user wants to **see a real nested hierarchy** (Drivers as chats
  nested under the Foreman session), not everything attached to the CoS.
- The user dislikes the **pure** dynamic-workflow experience because they intervene during
  implementation; the hybrid must keep live steering (section 6).
- Ask before launching anything costly; report cost per run.

## 4. What series 01–07 established

Full table: [tests/README.md](./tests/README.md). Full analysis:
[03-comparison-report.md](./03-comparison-report.md).

| Run | Engine | Result | Total USD | Per CR |
|-----|--------|--------|----------:|-------:|
| 04a | Opus Foreman session + `factory.py` | 5/5 | 1.06 | 0.21 |
| 04b | Sol Foreman session + `factory.py` | 4/5 | 0.68 | 0.14 |
| 06b | Sol Foreman, nested Drivers, `BOARD.md` | 7/7 | 0.62 | 0.12 |
| 07 | **Dynamic workflow**, Luna Coder + Inspector | 7/7 | **0.028** | **0.006** |

Key facts, all measured:

1. **Orchestration is the bill.** In session designs, 96 % of the cost is Foreman and Driver main
   sessions re-sending a ~30k-token prefix on every call. Coder + Inspector (Luna custom agents,
   ~2.7k prefix) are ~4 %. The workflow removes the main sessions: orchestration costs $0.
2. **Model choice** is the main lever inside session designs: Sol instead of Opus cut the Foreman
   cost by 69 %.
3. **State tooling does not matter for cost**: `factory.py` CLI vs `BOARD.md` gave the same bill.
4. **`/every` is poison** on any session that uses host tools: scheduled *and* normal turns hang
   on `tool_search_tool` (series 03 and 06). Do not use it.
5. Session-design races: a Driver can report DONE before reading a queued change, and the Foreman
   then sends a FINAL that is later superseded ("latest FINAL wins"). Messages to a busy CoS
   arrive only between its turns (6 min delay observed).
6. Host hierarchy is **two levels only**: a session and its chats. A Foreman created as an
   `independent` session gets its Drivers as nested chats; it cannot itself sit under the CoS.
   `delete_session` on the Foreman removes all nested Driver chats **and their telemetry**:
   archive `events.jsonl` first.
7. **Caveat**: all CRs so far were toy-sized (`stats.py` functions). On real CRs the Coder and
   Inspector share will grow; the 22× ratio will shrink. Measuring the real ratio is the point
   of series 08.

## 5. Dynamic workflow cheat sheet (CLI 1.0.105, experimental)

Docs (local, `web_fetch` was blocked):
`~/.copilot/pkg/darwin-arm64/1.0.105/copilot-sdk/docs/workflows.md`.

- Location: `<repo>/.github/extensions/<name>/extension.mjs`. Keep it **untracked** (or outside
  CR branches) so worktrees do not carry it.
- Import: `import { defineWorkflow, joinSession } from "@github/copilot-sdk/extension";`
  (resolved automatically), end the file with `await joinSession({ workflows: [wf] });`.
- `ctx` API: `agent(prompt, {label, schema, model, agent, reasoningEffort, contextTier})`,
  `parallel`, `pipeline`, `step`, `pause`, `log`, `phase`, `args`.
- `meta.limits`: `maxConcurrentSubagents`, `maxTotalSubagents`, `timeoutSeconds`,
  `maxAiCredits` (1 credit = $0.01). **Always set `maxAiCredits`.**
- Identical `ctx.agent` calls are memoized: give every call a **unique `label`**
  (`CR-3:coder:r2`).
- `agent: "coder"` resolves `<repo>/.github/agents/coder.agent.md` (its `model:` applies).
- Not supported: nested workflows; `write_agent` on workflow subagents (a running Coder cannot be
  steered; changes are picked up between steps).
- Headless run (what series 07 used):

  ```bash
  cd <lab>/repo
  GITHUB_COPILOT_PROMPT_MODE_EXTENSIONS=true copilot --experimental --allow-all-tools \
    --add-dir <lab> --add-dir /private<lab> \
    workflow run factory --args '{"lab":"<lab>"}' --result-file <lab>/result.json
  ```

  Without `--add-dir` (both the path and its `/private` realpath on macOS for `/tmp`), every shell
  call is denied ("no interactive user response"). `--allow-all-tools` means: run only in a
  dedicated lab or worktree, never where secrets live.
- A headless run leaves a session-state directory and an **idle host session** visible in
  `list_sessions`. Archive its `events.jsonl`, then delete that session.

Reference implementation: [tests/07-dynamic-workflow/kit/](./tests/07-dynamic-workflow/kit/)
(`extension.mjs`, `inbox.json`, `setup.sh`). Agent definitions:
`tests/06-nested-steered/kit/repo-template/.github/agents/{coder,inspector}.agent.md`.

## 6. Target design for series 08 (the hybrid)

```
User ⇄ CoS chat ──writes──▶ inbox.json ◀──reads between steps── factory workflow (Foreman)
          ▲                                                        │  per CR: worktree
          └──────────reads── status.json / run log ◀──writes───────┤  Coder → Inspector → rule
                                                                   └─ escalation ladder
```

- **Inbox** (outside the repo, in the lab dir): `{closed, crs[], changes[], ops[]}`. The CoS turns
  each user direction into one entry: `add`, `change`, `reorder` (priority), `reopen` (a done CR,
  e.g. PR feedback), `cancel`, `close`. The workflow re-reads it between steps: zero tokens.
- **Status** (new in 08): the workflow writes `status.json` after each step (CR, round, phase,
  last verdict, commit, escalation level). The CoS reads it to answer "where is CR-3?" without
  waking any LLM. The CoS can also read the CR worktree directly to review work in progress.
- **Escalation ladder, in code**:
  1. Rounds 1–2: Luna Coder, Luna Inspector, rule (`blocking == []` and no late change → accept).
  2. Still blocking after round 2: one **judge** call `ctx.agent(..., {model: "gpt-6.1-sol",
     schema: {decision: fix|accept|escalate, reason}})`.
  3. `escalate`: rerun the Coder with `model: "gpt-6.1-sol"` (verify that `model` overrides the
     custom agent's model; record the result).
  4. Still failing: mark the CR `needs-driver` in `status.json` and stop working on it. The CoS
     then creates an **interactive Driver session** (independent, in that worktree) for a human
     deep-dive. This is the only place an LLM session is used.
- **Stack** (optional in 08): dependent CRs branch from their parent CR branch instead of `main`;
  a final step opens stacked PRs/MRs (`gh` or `glab stack`).
- **No `/every` anywhere.** The workflow `sleep`s when idle; it exits when `closed` and all CRs
  are done, cancelled or `needs-driver`.

## 7. Series 08 protocol

Create `tests/08-hybrid-real-repo/` in this folder with `README.md`, `kit/` and `results/`,
following the layout of series 06 and 07.

Scenario (adapt the CRs to the real project; they must be **real, non-toy** CRs, large enough for
the Coder cost to dominate):

| # | Check | Pass criterion |
|---|-------|----------------|
| W1 | 4+ real CRs delivered in parallel worktrees | all branches build and pass the project's quality gates |
| S1 | `add` mid-run | new CR picked up and delivered |
| S2 | `change` on a running CR | applied in the next round; wasted work ≤ 1 Coder call |
| S3 | `reorder` | a lower-priority queued CR starts after a higher one added later |
| S4 | `reopen` of a delivered CR (simulated PR feedback) | new round on the same branch, new commit |
| S5 | `cancel` | CR stops at the next step boundary, worktree left clean |
| Q1 | Inspector catches a real defect, loop fixes it | recorded in `status.json` and the run log |
| E1 | forced escalation (a CR designed to be hard, or a test flag) | judge called; Sol Coder called; outcome recorded |
| E2 | hand-off to an interactive Driver session | CoS creates it from `needs-driver`; it finishes; session deleted after archiving telemetry |
| R1 | CoS answers "status of CR-x?" from `status.json` alone | no extra LLM call besides the CoS turn |
| L1 | clean end of life | run returns; no idle session, process or schedule left |
| C1 | cost | per CR, per role, per escalation level; compare with 06b and 07 |

Measure and record for every run:

- Cost: `UV_NO_CONFIG=1 uv run --quiet <this folder>/evidence/scripts/session_cost.py
  <session-state-dir>/events.jsonl`. Find the run's directory with
  `ls -t ~/.copilot/session-state | head` or `grep -l 'CR-1:coder' ~/.copilot/session-state/*/events.jsonl`.
  Do **not** use `totalNanoAiu` from `session.usage_checkpoint` events (partial, inconsistent).
- Also price the CoS turns spent steering (the CoS's own `events.jsonl`, turns in the run window)
  so the hybrid's true total is known. Series 01–07 excluded the CoS cost.
- Duration, rounds per CR, escalations, wasted Coder calls, tokens per role.
- Archive `events.jsonl`, `inbox.json`, `status.json`, `result.json` and the run log into
  `tests/08-hybrid-real-repo/results/` **before** deleting any session.

## 8. Reports to complete (so a later session can resume)

When series 08 is done (or abandoned), update **all** of these in this folder:

1. `tests/08-hybrid-real-repo/README.md`: goal, setup, exact commands, checks table with
   pass/fail, cost table, limits observed (same structure as series 07).
2. [tests/README.md](./tests/README.md): add the 08 row to the comparison table and to the
   cost-per-CR table; update "Design decisions supported so far".
3. [03-comparison-report.md](./03-comparison-report.md): add solution **E. Hybrid** to sections
   2–4, revise the recommendations (section 6) and open risks (section 7) with the real-CR
   ratio, replace section 8 with the next proposal.
4. [01-design.md](./01-design.md): **not yet updated since series 01**. Rewrite it to the
   consolidated design (workflow Foreman, CoS inbox, escalation ladder, no `/every`), citing the
   series that support each decision.
5. This file: append a dated entry to section 10 (what was done, where, what is next).

Keep the reports factual: measured numbers, the exact commands, what failed and why.

## 9. Known traps

- `send_message` delivery is only `queue` or `steer`; there is no interrupt.
- A Foreman *session* (if you fall back to the session design) cannot delete its own chats;
  only the CoS can, and deletion erases the nested telemetry.
- Sol tends to drop `relationship: "independent"` when it creates sessions; state it explicitly.
- `sed` on this machine is GNU: `sed -i` without `''`.
- Headless workflows cannot ask for approval: pre-grant with `--allow-all-tools` and `--add-dir`.
- Labels must be unique per `ctx.agent` call, or the call is served from memo and does nothing.
- Worktrees created by the workflow must be removed at the end (`git worktree remove`) or listed
  in the results for the user to clean.

## 10. Log

- 2026-10-29: series 01–07 complete; comparison report written; this handoff written. Next:
  series 08 in another project, run by a new session.
