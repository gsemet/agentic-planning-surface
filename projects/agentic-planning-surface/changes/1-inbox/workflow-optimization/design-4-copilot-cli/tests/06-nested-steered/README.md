# Series 06 — Nested hierarchy with live steering

## Goal

Validate the full CoS → Foreman → Drivers loop with a visible nested hierarchy, mid-run steering
from the CoS, and a clean end of life where the Foreman stops its own heartbeat.

## Setup

| Item | Value |
|------|-------|
| Foreman | `gpt-6.1-sol`, **independent** session created by the CoS |
| Drivers | 4 × `gpt-6.1-sol`, chats nested in the Foreman session (no `relationship`), own worktree |
| Coder / Inspector | custom agents in the toy repo, `gpt-5.6-luna` |
| State | `BOARD.md` (markdown table, edited by the Foreman only) — no state script |
| Heartbeat | `/every 3m heartbeat`, bash-only scheduled turn |
| Lab | `/tmp/crf-labs/06` (`kit/setup.sh /tmp/crf-labs/06 <cos-link>`) |

## Scenario

1. CoS creates the Foreman and queues `/every 3m heartbeat`.
2. Foreman hires 4 Drivers (CR-1..CR-4).
3. While Drivers work, the CoS sends:
   - `[CoS] add CR-5 ...` (new task mid-run);
   - `[CoS] change CR-2 ...` (spec change on a running CR).
4. Each Driver delivers `DONE` to the Foreman.
5. Foreman stops its own heartbeat, sends `FINAL` to the CoS.
6. CoS records costs, then deletes the Foreman session and checks that nothing is left.

## Checks

Run 06 used the heartbeat. Run 06b is identical except that it has **no heartbeat**, and the
CoS orders were sent right after the Foreman started (lab `/tmp/crf-labs/06b`).

| # | Check | 06 (heartbeat) | 06b (no heartbeat) |
|---|-------|----------------|--------------------|
| H1 | Drivers nested under the Foreman in the UI | **pass** | **pass** |
| H2 | Foreman hires and steers Drivers through session tools only | pass | pass |
| S1 | CR-5 added mid-run is hired and delivered | not reached (wedge) | **pass**: queued until a slot freed (max 4), delivered |
| S2 | CR-2 change reaches the Driver and the result honours it | not reached | **pass**: Driver delivered round 1, then applied the change as *defer* in round 2 (`3a1c73f`, tie rule + `ValueError`) |
| E1 | Heartbeat turns complete | **fail**, see below | n/a |
| E2 | Foreman stops its own heartbeat | **fail**: it wedged while searching for a tool to do it | n/a |
| E3 | Deleting the Foreman session removes everything | **pass**: Foreman + 4 nested Driver state dirs gone, no process left | **pass** |
| C1 | Cost | $0.55 for 4 CRs (Foreman 0.23) | **$0.62 for 5 CRs + 1 change** (Foreman 0.20) |

## Results

### Run 06: the heartbeat poisons the Foreman session

- 4 Drivers hired in parallel at 11:43:32; all 4 delivered (1 round, Inspector pass) by 11:44:34.
- `/every 3m heartbeat` was created at 11:43:47. At 11:44:38, in a **normal** turn (woken by the
  CR-2 DONE message, not by the schedule), the Foreman called `tool_search_tool` to look for a
  way to stop its heartbeat. The call never returned (`external_tool.requested` without
  `completed`). Before the schedule existed, `create_session` and `get_current_session` worked.
- New finding: once a session owns an active `/every`, host-served tools can hang even outside
  scheduled turns. A Foreman needs host tools to steer, so **a Foreman must never own a schedule**.
- `send_message` only accepts `queue` and `steer`; there is no interrupt. The wedged Foreman
  could only be removed with `delete_session` (E3).

### Run 06b: no heartbeat, full steering

| Role | Model | USD |
|------|-------|----:|
| Foreman | gpt-6.1-sol | 0.199 |
| Driver CR-1 | gpt-6.1-sol | 0.113 |
| Driver CR-2 (2 rounds) | gpt-6.1-sol | 0.119 |
| Driver CR-3, CR-4, CR-5 | gpt-6.1-sol | 0.065 each |
| Coder + Inspector (all CRs) | gpt-5.6-luna | 0.024 |
| **Total** | | **0.625** |

- Duration: 11:46:52 → 11:48:56 (about 2 min).
- **Race on FINAL**: the CR-2 Driver first sent `DONE` for round 1, then processed the queued
  change and sent a second `DONE`. The Foreman had already sent `FINAL` in between. Fix: the
  Driver must read its queue before reporting, or the Foreman must wait for every forwarded
  change to be acknowledged. The FINAL received by the CoS indeed lists CR-2 at `d62f6e0`
  (pre-change) instead of `3a1c73f`. The Foreman then self-corrected: on the late CR-2 report it
  sent a second FINAL ("Updated CR-2 completion supersedes its earlier report", `3a1c73f`). The
  outcome is correct, but the CoS must treat FINAL as "latest wins", not as a terminal signal.
- **Delivery latency to a busy CoS**: FINAL was sent at 11:48:48Z with delivery `queue` and reached
  the CoS only at 11:54Z, when its turn ended. Messages to the CoS are read between its turns, so
  a busy CoS sees reports late.
- No state script: the Foreman edited `BOARD.md` with `apply_patch`. It cost about the same as the
  `factory.py` CLI of series 04b (Foreman 0.20 vs 0.18).

Telemetry: `results/telemetry/` (06) and `results/06b/telemetry/` (06b), boards in `results/`.
