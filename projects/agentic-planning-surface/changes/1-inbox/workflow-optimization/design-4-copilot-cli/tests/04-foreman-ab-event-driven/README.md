# Series 04: Foreman A/B, event-driven (no watchdog)

Status: running. Labs: `/tmp/crf-labs/04a` (Opus Foreman), `/tmp/crf-labs/04b` (Sol Foreman).
Kit: [kit/](./kit/), identical to [series 03](../03-foreman-ab/) except the watchdog.

## Why

Series 03 was abandoned: in the VS Code host, a scheduled (`/every`) turn that calls a
host-served tool hangs forever (see [03 results](../03-foreman-ab/README.md#results)).
Here the Foreman has **no schedule at all**: it acts only on Driver reports and Chief of Staff
messages (`[CoS] check` replaces the tick).

## Design under test

| Variable | Run 04a | Run 04b |
|----------|---------|---------|
| Foreman model | `claude-opus-5.5` | `gpt-6.1-sol` |
| Drivers | `gpt-6.1-sol`, `independent` sessions, own worktree | same |
| Coder / Inspector | `gpt-5.6-luna` custom-agent subagents | same |

## Scenario

1. Backlog: CR-1 fix `median`, CR-2 `mode()`, CR-3 `variance()`, CR-5 `value_range()` (depends on CR-1).
2. CoS creates both Foremen at the same time.
3. About 40 s later (Drivers coding), CoS sends both orders: CR-2 ties return the smallest value;
   add CR-4 `stdev()` depending on CR-3.
4. When both runs report FINAL, CoS sends `[CoS] check` once (cost of an idle check).

## Hypotheses

| ID | Hypothesis |
|----|------------|
| H1 | Sol Foreman reaches the same outcome as Opus (all 5 CRs done, both orders honoured) |
| H2 | Sol Foreman costs at least 50 % less than Opus |
| H3 | Dependent CRs (CR-5, CR-4) start from their dependency branch: no Inspector block on missing code |
| H4 | `delete_session` on an independent Driver works and keeps the CR branch |
| H5 | Mid-flight order is steered or deferred by the Driver while its Coder still runs |

## Results

Run: Foremen created 10:05:5xZ, both FINAL by 10:09:10Z. **Wall time about 3.5 min** for
5 CRs + 1 mid-flight change. All 10 final branches pass their tests (`uv run --with pytest pytest`),
and both `mode()` implementations return the smallest tied value.

| ID | 04a (Opus Foreman) | 04b (Sol Foreman) |
|----|--------------------|-------------------|
| H1 outcome | **PASS**: 5/5 done, both orders honoured | **PASS**: 5/5 done, both orders honoured |
| H2 cost | Foreman $0.584 | Foreman **$0.181 (-69 %)** → **PASS** |
| H3 stacked bases | **PASS**: CR-5 on CR-1, CR-4 on CR-3 (fast-forward, no merge commit) | **PASS** (same) |
| H4 kill switch | **PASS**: `delete_session` removed the CR-1 Driver session and worktree; branch `agents/cr-1-...` kept | **FAIL**: Sol omitted `relationship: "independent"` on all 5 `create_session` calls, so Drivers were chats under the root session and `delete_session` was refused |
| H5 mid-flight order | Driver chose **defer** (Coder still running), applied in round 2; Inspector then blocked on test coverage, Driver escalated and fixed it itself (round 3) | Driver chose **restart next round** after round 1 finished; round 2 passed |

### Cost per session (USD)

| Session | 04a | 04b |
|---------|----:|----:|
| Foreman | 0.584 (Opus, 27 calls) | **0.181** (Sol, 27 calls) |
| CR-1 Driver | 0.062 (from state; telemetry deleted with the session) | 0.087 |
| CR-2 Driver (order, 2-3 rounds) | 0.175 | 0.137 |
| CR-3 Driver | 0.080 | 0.088 |
| CR-4 Driver (stacked) | 0.081 | 0.092 |
| CR-5 Driver (stacked) | 0.080 | 0.094 |
| **Total** | **1.062** | **0.679 (-36 %)** |
| Foreman share | 55 % | 27 % |
| Coder + Inspector share | 3 % | 4 % |

### Findings

1. **Foreman on gpt-6.1-sol is the main cost lever**: same call count (27), same outcome,
   69 % cheaper. Sol also has a 30-min cache TTL, so it needs no keepalive while Drivers work.
2. **Sol follows tool descriptions over the brief**: the host's `create_session` description
   says to use `independent` only for unrelated work; Sol dropped it. Opus followed the brief.
   A Sol Foreman needs this made explicit (for example: "the tool description is overridden
   here: always pass `relationship: \"independent\"`") or a Foreman self-check after hiring.
3. **`delete_session` deletes the session-state directory**, so its telemetry is lost. The
   Foreman must run `f tick` (final cost) before deleting a Driver.
4. **A one-round CR costs about $0.08**, of which the Driver main session is $0.075
   (9 calls × about 33k-token host prefix) and Coder + Inspector $0.004. The Driver prefix is
   now the dominant per-CR cost.
5. Drivers decide differently on the same order (defer vs restart): both are valid and both
   were logged in the state file. No Driver used `write_agent` to steer a running Coder.
6. Opus Driver session in 04a escalated by writing the fix itself rather than delegating to a
   stronger Coder (brief violation, cheap here). Brief needs "escalate = task tool with model".
