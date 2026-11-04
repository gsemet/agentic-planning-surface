# Series 03: Foreman A/B (Opus vs gpt-6.1-sol), self-paced watchdog, stacked bases

Status: running. Labs: `/tmp/crf-labs/03a` (Opus Foreman), `/tmp/crf-labs/03b` (Sol Foreman),
built by [kit/setup.sh](./kit/setup.sh) `<lab> <run-id> <wake-seconds>`.

## Goal

Series 02 showed the Opus Foreman costs 53 % of the run. This series runs the **same scenario
twice in parallel**, changing only the Foreman model, and fixes the series 02 gaps.

| Variable | Run 03a | Run 03b |
|----------|---------|---------|
| Foreman model | `claude-opus-5.5` (cache TTL 300 s) | `gpt-6.1-sol` (cache TTL 1800 s) |
| Self-paced re-arm delay | 270 s (inside TTL) | 1500 s (inside TTL) |
| Everything else | identical | identical |

## Changes since series 02

| Series 02 finding | Change in [kit/](./kit/) |
|-------------------|--------------------------|
| Fixed `/every` cannot be stopped | Watchdog is **self-paced** (`/every <prompt>` with no interval); the Foreman re-arms with `manage_schedule` while work remains and stops by not re-arming |
| Dependent CR branched from `main` | `f tick` prints `base=<dep branch>`; Foreman passes `Base:` to the Driver; Driver merges it before delegating |
| `tick` missed cost of CRs finished between ticks | Done CRs get one final cost read (`cost_final`) |
| Kill switch unknown | All Drivers are `independent` sessions; Foreman calls `delete_session` on CR-1's Driver after DONE |
| Markers collide across parallel runs | Marker is `[<run> CR-N driver]` (`FACTORY_RUN`) |

## Scenario (same for both runs)

1. Backlog: CR-1 fix `median`, CR-2 add `mode()`, CR-3 add `variance()`, CR-5 `value_range()`
   depending on CR-1 (stack test).
2. CoS creates the Foreman: "Read `$LAB/FOREMAN.md` and follow it."
3. CoS sends the self-paced watchdog: `/every watch the factory as described in FOREMAN.md`.
4. About 40 s later, while Drivers are coding, CoS sends both orders at once:
   CR-2 ties return the smallest value; add CR-4 `stdev()` depending on CR-3.

## Hypotheses

| ID | Hypothesis |
|----|------------|
| H1 | Sol Foreman completes the same scenario with equal outcome (all CRs done, orders honoured) |
| H2 | Sol Foreman costs at least 50 % less than Opus |
| H3 | Self-paced watchdog: `manage_schedule` is available in the scheduled turn, and the schedule ends by itself when the run is over |
| H4 | Dependent CRs (CR-5, CR-4) start from their dependency branch: no Inspector block on missing code |
| H5 | `delete_session` on an independent Driver works and keeps the CR branch |
| H6 | Mid-flight order (Driver still coding) is steered or deferred, not only reopened |

## Results

### Run interrupted: scheduled turns wedge on host tools (both runs, 3/3 reproduced)

| Time (Z) | 03a (Opus) | 03b (Sol) |
|----------|------------|-----------|
| 09:58:5x | Foreman hires CR-1..3 (independent, base main) | same |
| 09:59:48 | Self-paced `[Scheduled prompt #1]` fires | same |
| 09:59:49/53 | Foreman calls `tool_search_tool` (to load `manage_schedule`): `external_tool.requested`, **never completed** | same |
| 10:00:3x | Drivers finish CR-1..3 (round 1, Inspector pass), reports queued at the Foreman | same |
| 10:02+ | CoS orders queued behind the wedged turn; CR-4 never added, CR-5 never hired | same |
| 10:03 | `send_message` with `delivery: steer` has no effect | same |

The same wedge happened in series 01 (T2.1, after `/every list`). **In the VS Code host, a
scheduled (`/every`) turn that calls a host-served tool (`tool_search_tool`, and very likely
`send_message`, `create_session`) hangs forever.** Scheduled turns only work with CLI-native
tools (`bash`, `view`): series 02 ticks (bash only) completed. A wedged Foreman blocks every
queued Driver report and Chief of Staff order, so it is a single point of failure.

Consequence for the design: **no `/every` watchdog on the Foreman in the host.** The Foreman
must be purely event-driven (Driver reports, CoS orders). Stale detection moves to the Chief of
Staff (on demand) or to a bash-only watchdog that can only write to the state file.

Hypotheses H1, H2, H3, H5, H6: not measurable in this run (Foreman wedged before the orders).
H4: not reached (CR-5 never hired).
