# Series 02: Foreman-driven factory (Foreman hires its own Drivers)

Status: running. Lab: `/tmp/crf-labs/02-foreman-driven` (built by [kit/setup.sh](./kit/setup.sh)).

## Goal

Series 01 created every session from the Chief of Staff. Here the Chief of Staff creates **only
the Foreman**; the Foreman reads a shared state file, hires Drivers, relays Chief of Staff orders,
and stops when all CRs are done. Drivers delegate to custom-agent subagents (Coder, Inspector).

## Hypotheses

| ID | Hypothesis | Pass criterion |
|----|------------|----------------|
| H1 | The Foreman can hire Drivers with `create_session` (worktree each) | 3 Drivers in 3 worktrees, titles `[CR-N driver]` |
| H2 | `relationship: "independent"` from the Foreman gives a separate session tree | `list_sessions` shows the Driver outside the Chief of Staff session |
| H3 | A Driver can report back to the Foreman with `send_message` and the Foreman reacts | Foreman hires the next ready CR within 1 min of a `DONE` report |
| H4 | `/every 4m` sent by the Chief of Staff via `send_message` schedules a watchdog in the Foreman | Scheduled-prompt turns visible every 4 min |
| H5 | A mid-run Chief of Staff order reaches the right Driver and is handled (steer/restart/defer) | Note logged in state; final code honours the order |
| H6 | Driver idles at zero cost while its background Coder runs | No Driver usage records between delegation and notification |
| H7 | Run stays under budget | Total < $3.00; Coder+Inspector < 10 % |

## Setup

- Toy repo: [kit/repo-template/](./kit/repo-template/) (`src/stats.py`, buggy `median`), with
  custom agents [coder](./kit/repo-template/.github/agents/coder.agent.md) and
  [inspector](./kit/repo-template/.github/agents/inspector.agent.md) on `gpt-5.6-luna`.
- State: [kit/factory.py](./kit/factory.py) via wrapper `$LAB/f`, single JSON file, lock + atomic write.
- Briefs: [kit/FOREMAN.md](./kit/FOREMAN.md), [kit/DRIVER.md](./kit/DRIVER.md).
- Roles and models: Foreman `claude-opus-5.5` (host default effort), Drivers `gpt-6.1-sol`,
  Coder/Inspector `gpt-5.6-luna`.

## Scenario

1. CoS creates the Foreman: "Read `$LAB/FOREMAN.md` and follow it."
2. CoS sends `/every 4m tick` to the Foreman (H4).
3. Initial backlog: CR-1 fix `median`, CR-2 add `mode()`, CR-3 add `variance()`.
4. Once Drivers are coding, CoS order 1: "CR-2: on ties, mode returns the smallest value" (H5).
5. CoS order 2: "Add CR-4 `stdev()` (population), depends on CR-3" (H3: hired after CR-3 done).
6. Run ends when the Foreman replies `FINAL`.

## Measurements

- Hierarchy: `list_sessions` after hiring.
- Per-session cost: [../../evidence/scripts/session_cost.py](../../evidence/scripts/session_cost.py)
  on each session's `events.jsonl`.
- Latencies: timestamps of report → Foreman turn → next hire.

## Results

Run: 2026-10-29 09:33:29Z (Foreman created) → 09:38:30Z (CR-4 done). Wall time **5 min** for
4 CRs + 1 reopened CR. All commits are in `/tmp/crf-labs/02-foreman-driven/repo.worktrees/*`.

| ID | Verdict | Evidence |
|----|---------|----------|
| H1 | **PASS** | Foreman hired 3 Drivers in 75 s (worktrees `cr-N-driver-implementation`, branches `agents/cr-N-...`), then CR-4 after the order |
| H2 | **PASS** | `relationship: "independent"` (CR-1) created a top-level session `ahp-session/74e245c9...`, listed on its own by `list_sessions`. Default relationship (CR-2..4) gives chats under the Chief of Staff root session |
| H3 | **PASS** | Each `[CR-N] DONE` arrived as a new Foreman turn (from the independent session too). Report → Foreman hire: under 10 s |
| H4 | **PASS (but no stop)** | `/every 4m tick` sent with `send_message` created `schedule #1` in the Foreman. **There is no way to stop it from the host**: no agent tool, `/every` alone errors (the stop UI is the TUI picker only), `delete_session` refuses chat links (they resolve to the root session) |
| H5 | **PASS** | Order at 09:35:09: Foreman logged it, reopened CR-2, messaged its Driver; Driver decided "round 2" (note logged), new commit `42ca14b` at 09:35:59 (**50 s**). CR-4 added and hired in the same turn |
| H6 | **PASS** | Drivers idle while their background Coder runs; woken by `agent_idle` notification |
| H7 | **PASS** | Total **$1.11** (< $3). Coder + Inspector $0.036 = **3 %** |

### Cost per session

| Session | Model | Calls | Cache read | Cache write | USD |
|---------|-------|------:|-----------:|------------:|----:|
| Foreman | claude-opus-5.5 | 27 | 1,500,904 | 37,195 | **0.587** |
| CR-1 Driver (independent) | gpt-6.1-sol | 9 | 278,866 | 35,782 | 0.125 |
| CR-2 Driver (2 rounds, reopened) | gpt-6.1-sol | 17 | 534,200 | 35,510 | 0.155 |
| CR-3 Driver | gpt-6.1-sol | 10 | 306,457 | 19,813 | 0.088 |
| CR-4 Driver (2 rounds) | gpt-6.1-sol | 18 | 584,927 | 21,379 | 0.128 |
| All Coders + Inspectors (13 subagents) | gpt-5.6-luna | 80 | | | 0.036 |
| **Total** | | | | | **1.11** |

Per CR: **$0.28** including the Foreman, $0.14 Driver + subagents only.

### Findings

1. **The Foreman is 53 % of the bill**: Opus main session, prefix about 55k tokens, 27 calls,
   each call about $0.011 even fully cached. The fix is fewer and cheaper Foreman calls, not
   cheaper Coders.
2. **Driver main sessions are 47 %**: about 30-35k prefix × 9-18 calls. A Driver turn that only
   delegates and waits still re-sends the full host prefix.
3. **Dependency base branch is a design gap**: CR-4 was branched from `main`, not from CR-3.
   The Inspector caught it (blocking), the Driver merged CR-3 in round 2. The Foreman must pass
   a base branch for dependent CRs (stack) instead of relying on the Inspector.
4. **`factory.py tick` cost lookup missed** CR-3 and CR-4 (reported $0.000): the marker lookup
   scans only recent session dirs at tick time. Fix before series 03.
5. **Fixed-interval `/every` cannot be stopped in the host.** It keeps ticking the Foreman at
   about $0.012-0.025 per tick (Opus, warm) until the window closes. Use a **self-paced** schedule
   (the model re-arms with `manage_schedule wakeup`, 60-3600 s, and ends it by not re-arming) or
   no schedule at all.
6. **A session can wedge**: in series 01, the T2.1 chat waits forever on a host
   `tool_search_tool` call inside a scheduled turn (no events since 09:37:20Z). It costs nothing
   but blocks all queued messages. A Foreman needs a liveness check from the Chief of Staff.
7. Independent sessions are top-level, so `delete_session` should work on them: candidate
   kill switch for Drivers (test in series 03).
