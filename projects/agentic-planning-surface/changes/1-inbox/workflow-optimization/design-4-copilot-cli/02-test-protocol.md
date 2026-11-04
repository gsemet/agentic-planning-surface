# Test protocol: is design 4 feasible on Copilot CLI, and at what cost?

Each test proves or kills one assumption of [01-design.md](./01-design.md).
Tests are ordered so that a failure early saves the cost of later tests.

## 0. Rules for every test

- **Cheapest model that can answer the question**: `gpt-6-luna` unless the test is about a
  model. Toy tasks only (one file, a few lines).
- **Cap** per test: host sessions have no credit flag, so the tester meters with
  `copilot-session-usage` and deletes the session at the cap.
- **Trimmed sessions**: custom agents with explicit tool lists once T1.2b passes.
- **Pinned CLI version**: 1.0.105. Record `copilot --version` in each result.
- **Measure, do not trust**: after each test run
  `uv run evidence/scripts/session_cost.py <events.jsonl>` and store the output.
- **Result file**: `results/T<id>.md` with hypothesis, command, raw numbers, verdict
  (PASS / FAIL / PARTIAL), cost.
- **Isolation**: tests run in a throwaway repo (`/tmp/crf-lab`), never in a real project.

Estimated total budget for the whole protocol: **under $3** (about 300 credits).

## Phase A: control plane in the VS Code Agents host (blocking, run first)

| ID | Hypothesis | Method | Pass criteria | Cap |
|----|------------|--------|---------------|----:|
| T1.1 | A created session can itself create sessions (CoS → Foreman → 3 Drivers) | CoS creates a Foreman stub on `gpt-6-luna`; it creates 3 Drivers with `worktree: true`, each writes one file | 3 files in 3 worktrees; Drivers visible in `list_sessions` | 30 |
| T1.2 | The `model` passed to `create_session` is honoured | Check `usage_record.model` of each created session | Exact match | 0 |
| T1.2b | A created session can run on a custom agent with a tool allowlist and a reasoning effort | Try: agent named in the prompt, `.agent.md` in the workspace, `/agent` as first prompt line | `availableToolCount` and `reasoningEffort` in `usage_record` match the agent file | 30 |
| T1.3 | `copilot-session-usage` reads a host session while it is still running | Run `--agent cli analyze <dir> --query` on a live Driver | Cost matches `session_cost.py` | 0 |
| T1.4 | `factory.py` survives concurrent writers | 6 parallel processes, 200 writes each | Valid JSON, no lost update | 0 |

## Phase B: messaging, wake-up, scheduling (the core requirement R2)

| ID | Hypothesis | Method | Pass criteria | Cap |
|----|------------|--------|---------------|----:|
| T2.1 | `/every` works in a host session and keeps an Opus cache warm at 4 min | Foreman stub on `claude-opus-5.5` with `/every 4m factory.py tick` for 30 min | Ticks fire; `cacheReadTokens` high on every tick; cost per tick measured | 60 |
| T3.1 | A Driver message to the Foreman lands quickly, whether the Foreman is idle or in a tick | Driver sends "done" at a random time | Latency measured in both cases | 30 |
| T3.2 | Background subagent completion wakes an idle Driver | Driver starts a Coder (`sleep 120` then edit) in background and ends its turn | New Driver turn after the Coder ends, with no outside message | 30 |
| T3.3 | A Foreman message to an idle Driver whose Coder runs is handled at once | Same setup; Foreman sends "rename X to Y" after 20 s | Driver turn starts in < 10 s and chooses steer, restart or defer | 30 |
| T3.4 | `delete_session` stops a Driver and its subagents | Delete a Driver with a running Coder | No `usage_record` after deletion; worktree state recorded | 30 |
| T3.5 | The Driver chooses well between steer, restart and defer | 6 scripted messages (typo note, API rename, scope cut, ...) | Matches a pre-written table at least 5 of 6 | 60 |
| T3.6 | Nesting depth: Driver session → Coder → helper subagent | Coder spawns an `explore` subagent | Three levels in events | 30 |

Kill condition: if T1.1 or T3.2 fails, re-grill before going on. If T2.1 fails, the watchdog
moves to `configureAutomation` (hourly) or to the Chief of Staff.

## Phase C: cache and pricing

| ID | Hypothesis | Method | Pass criteria | Cap |
|----|------------|--------|---------------|----:|
| T4.1 | Measured TTLs hold: 300 s Claude, 1800 s GPT | Two calls on `gpt-6-luna` 25 min apart, then 35 min apart; same for `claude-sonnet-5.5` at 4 and 6 min | `cacheReadTokens` high before TTL, near 0 after | 30 |
| T4.2 | A ping refreshes the TTL | GPT: call, ping at 25 min, call at 50 min (Opus covered by T2.1) | Third call reads from cache | 30 |
| T4.3 | A long-lived Opus Foreman stays affordable | Replay 3 h of ticks and 20 events; record compactions and their cache cost | Cost per hour and per compaction recorded | 60 |
| T4.4 | Trimmed tools shrink the prefix | Same prompt with full tools vs a 3-tool allowlist | `toolTokenCount` and cost ratio recorded | 30 |
| T4.5 | Subagents with the same agent file share a cached prefix | Two sequential Coders of the same custom agent | Second Coder's first call shows `cacheReadTokens > 0` | 30 |

## Phase D: model ladder and Inspector economics

| ID | Hypothesis | Method | Pass criteria | Cap |
|----|------------|--------|---------------|----:|
| T5.1 | `gpt-5.6-luna` max solves typical small CRs | 5 toy CRs with tests (bug fix, rename, add param, add test, small feature) | Success rate and cost per CR recorded | 60 |
| T5.2 | Escalating after failure is cheaper than starting on `gpt-6.1-sol` | Same 5 CRs on `gpt-6.1-sol` directly | Compare total cost; keep the cheaper policy | 60 |
| T6.1 | The Inspector finds planted defects | Coder output with 3 planted bugs (1 blocking, 2 minor) | Blocking found; false-positive count recorded | 30 |
| T6.2 | The Driver weighs critiques soundly within 2 rounds | Feed 4 Inspector verdicts with known values | Accept, rerun, escalate as expected | 30 |

## Phase E: isolation, stacks, measurement

| ID | Hypothesis | Method | Pass criteria | Cap |
|----|------------|--------|---------------|----:|
| T7 | Worktree Drivers cannot touch each other | Driver A asked to edit a path in worktree B | Refused or detected by the Foreman's post-check | 30 |
| T8 | A Stack manager can restack after a lower PR changes, on GitHub and GitLab | 3 stacked branches with `gh stack` and with `glab stack`; amend the bottom one; forge rules R2.5 | Upper branches rebased; conflicts reported | 30 |
| T9 | Local cost equals billed cost | Sum of `nanoAiu` for one day of tests vs `/usage` and the billing dashboard | Difference < 2 % | 0 |

## Phase F: end-to-end pilot

| ID | Hypothesis | Method | Pass criteria | Cap |
|----|------------|--------|---------------|----:|
| T10 | The whole factory delivers 5 CRs with live interventions, cheaper than design 3 | Real small backlog in a scratch repo; during the run the user adds one CR, reorders two, fixes one PR by hand, stops one | All interventions handled; total cost and cost per role recorded; orchestration < 20 % of total | 150 |

Baseline for comparison: the simulation in [evidence/local-telemetry-findings.md](./evidence/local-telemetry-findings.md)
(orchestration 99 %, $2.28 for 5 toy tasks).

## Deliverables of the protocol

1. `results/T*.md`, one per test.
2. Updated tables in [01-design.md](./01-design.md) §4 with measured values.
3. A go / no-go note per role, written before the pilot T10.
