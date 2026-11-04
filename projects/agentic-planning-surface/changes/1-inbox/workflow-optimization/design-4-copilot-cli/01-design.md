# Design 4: cost-controlled change-request factory on Copilot (VS Code Agents host)

Status: draft after four grilling rounds. Nothing is validated until
[02-test-protocol.md](./02-test-protocol.md) passes.
Requirements and user decisions: [00-requirements.md](./00-requirements.md) (R2.1 to R2.6).
Evidence: [evidence/](./evidence/).

## 1. Principles (each one backed by a measurement or a decision)

| # | Principle | Source |
|---|-----------|--------|
| P1 | Tokens pay for judgement only; queues, state and cost metering live in scripts | Simulation: orchestration was 99 % of $2.28 ([findings §3](./evidence/local-telemetry-findings.md)) |
| P2 | Workers on small models; frontier model only where judgement on the whole batch matters (Foreman) | Price table ([findings §2](./evidence/local-telemetry-findings.md)), R2.2 |
| P3 | One model per session for its whole life; escalation means a new subagent, never a switch | Model switch invalidates the cache ([billing research §2](./evidence/research-billing.md)) |
| P4 | Keep caches warm only where the TTL forces it: Opus Foreman ticks every 4 min (TTL 300 s); GPT roles have 30 min | `cacheTtlSeconds`, R2.3 |
| P5 | Minimal prefix through custom agents with explicit tool lists | Tool schemas cost 12k-22k tokens per call |
| P6 | State is read from a file, never awaited from an LLM | No completion notification; steer latency of minutes |
| P7 | Cost is metered from `events.jsonl`, per session, by a tool, not estimated by an LLM | R2.6 |
| P8 | A Driver receives messages only between turns, so it never blocks on its Coder | Messages are delivered at turn boundaries |

## 2. Topology

```text
User
 │  grills, hesitates, redirects
 ▼
Chief of Staff ── your chat in the VS Code Agents host
 │  create_session (once)          reads: factory.py status
 ▼
Foreman ── nested session, Claude Opus 5.5 low, custom "foreman" agent, /every 4m watchdog
 │  create_session per CR (worktree: true)      send_message (queue | steer)
 ▼                                                  ▲
Driver × N ── sibling sessions, gpt-6.1-sol,        │ "done" / "blocked" / "escalated"
 │            custom "driver" agent                 │ via send_message to the Foreman
 ├── Coder ── background subagent, gpt-5.6-luna, effort max
 ├── Inspector ── sync subagent, gpt-5.6-luna, effort max, read-only
 └── Coder+ ── escalated Coder on a bigger model, Driver's own decision
Stack manager ── optional session hired by the Foreman for PR/MR stacks

             factory-state.json  ◄── written only by factory.py (lock + atomic rename)
```

## 3. Roles

### 3.1 Chief of Staff

- Your conversation. It translates your intent into **orders** and never orchestrates itself.
- Creates the Foreman once with `create_session` and keeps its link in the state file.
- Sends orders to the Foreman with `send_message` (`queue`; `steer` only for urgent changes).
- Reads progress with `factory.py status` (one line per CR, a few hundred tokens), never by
  reading the Foreman's transcript (`get_session_context` is expensive).

### 3.2 Foreman

- **Session**: nested, `claude-opus-5.5`, reasoning effort low, custom agent `foreman` with a
  minimal tool list: shell (for `factory.py` and `copilot-session-usage`), `create_session`,
  `send_message`, `delete_session`. No file editing, no web, no MCP.
- **Inputs**: orders from the Chief of Staff, reports from Drivers, `/every 4m` watchdog ticks.
- **Duties**: translate orders into queue operations, start Drivers as dependencies allow,
  relay last-minute changes to the right Driver, approve or veto escalations, hire a Stack
  manager when CRs chain, enforce the budget, end when the queue is empty.
- **Watchdog tick** (every 4 min, keeps the Opus cache warm):
  1. `factory.py tick`: a script that refreshes each Driver's cost with
     `copilot-session-usage`, flags stale Drivers (no event for N minutes) and over-budget ones,
     and prints **only the anomalies**. An empty output means a one-line LLM answer.
  2. The Foreman acts only on anomalies.
- **Memory**: long-lived for the whole batch (R2.3). The state file is the source of truth, so
  compaction loses no decision.

### 3.3 Driver

- **Session**: sibling created by the Foreman with `create_session` (`worktree: true`), model
  `gpt-6.1-sol`, custom agent `driver`.
- **Loop**, one turn per step (P8):
  1. *Brief*: read the CR from the state file, write a short Coder brief.
  2. *Delegate*: start the Coder as a **background** subagent; end the turn (idle, no cost).
  3. *Wake-up*: Coder completion, or a Foreman message.
  4. *On message*: the Driver decides (R2.1): steer the Coder, cancel and re-brief, or defer the
     change to the next round. It records the decision with `factory.py note`.
  5. *On Coder done*: run the Inspector (sync).
  6. *Judge*: accept, re-run the Coder (at most **2 rounds**), or escalate to Coder+ and notify
     the Foreman (R2.4).
  7. *Deliver*: push, open or update the PR/MR with `gh` or `glab` following the forge rules
     (R2.5), report to the Foreman with `send_message`, set status with `factory.py`.

### 3.4 Coder and Inspector

- Custom agents `coder.agent.md` and `inspector.agent.md`, model `gpt-5.6-luna`, effort max.
- **Coder**: edit, shell, search. No web, no MCP.
- **Inspector**: read-only plus test runner, hostile prompt, JSON verdict
  `{blocking:[...], minor:[...], confidence}`.
- **Coder+**: same brief on `gpt-6.1-sol` or `claude-sonnet-5.5`, chosen by the Driver.

### 3.5 Stack manager

- Optional session on `gpt-5.6-luna`, hired by the Foreman when two or more CRs chain.
- Tools: git, `gh stack` or `glab stack`, forge rules R2.5.
- Restacks when a lower PR changes (including your manual fixes) and tells the Foreman which
  Drivers are affected.

## 4. State file

`factory-state.json`, in the change folder, outside every worktree.

```json
{
  "run": {"id": "...", "budget_usd": 10, "spent_usd": 2.4, "foreman": "<session link>"},
  "crs": [
    {"id": "CR-3", "title": "...", "status": "coding", "order": 2, "deps": ["CR-1"],
     "driver": "<session link>", "session_id": "<uuid>", "branch": "...", "pr": null,
     "round": 1, "coder_model": "gpt-5.6-luna", "spent_usd": 0.31, "budget_usd": 1.5,
     "last_event": "2026-10-29T10:12:00Z", "notes": ["API renamed, deferred to round 2"]}
  ],
  "orders": [{"at": "...", "text": "...", "ops": ["reorder CR-3 before CR-2"]}]
}
```

`factory.py` commands: `status`, `add`, `reorder`, `set`, `note`, `tick`, `cost`. Every write
holds a file lock and replaces the file atomically.

## 5. Cost model (to be confirmed by tests)

Prices observed on this account ([findings §2](./evidence/local-telemetry-findings.md)).

| Item | Assumption | Estimate |
|------|-----------|---------:|
| Foreman idle tick | 30k cached prefix, 1k new, 200 out, Opus | about $0.015 / tick, $0.22 / h |
| Foreman event handling | same, 1k out | about $0.03 / event |
| Driver call | 40k cached prefix, 1k out, gpt-6.1-sol | about $0.015 / call, ~10 calls per CR |
| Coder + Inspector round | gpt-5.6-luna, effort max (reasoning billed as output) | about $0.01-0.05 |
| **Per CR, no escalation** | | **about $0.20-0.30** |

Target from the requirements: orchestration (Foreman + Drivers) below the cost of the work it
drives, measured in T10.

## 6. Intervention flows (R2)

| User intent | Path | Who pays |
|-------------|------|----------|
| "Where are we?" | CoS → `factory.py status` | CoS only |
| "Tell CR-3 the API was renamed" | CoS → Foreman → `send_message` to Driver 3 → Driver decides | Foreman event + Driver turn |
| "I fixed PR #42 by hand" | CoS → Foreman → Stack manager restacks → affected Drivers | Foreman + stack + Driver turns |
| "Add a CR" / "Reorder" | CoS → Foreman → `factory.py add` / `reorder` | Foreman event |
| "Stop CR-5" | CoS → Foreman → `send_message` steer, then `delete_session` if it keeps running | Foreman event |

## 7. Open risks

| Risk | Test |
|------|------|
| `create_session` cannot start a session on a custom agent or with a reasoning effort | T1.2b |
| A created session cannot itself call `create_session` (Foreman creating Drivers) | T1.1 |
| `/every` does not exist in the VS Code host | T2.1 |
| A Driver message to the Foreman is delayed while the Foreman is busy | T3.1 |
| Background subagent completion does not wake an idle Driver | T3.2 |
| `delete_session` is not an effective kill switch | T3.4 |
| `copilot-session-usage` cannot read VS Code host sessions mid-run | T1.3 |
| Long-lived Opus Foreman compacts often, losing its cache | T4.3 |
