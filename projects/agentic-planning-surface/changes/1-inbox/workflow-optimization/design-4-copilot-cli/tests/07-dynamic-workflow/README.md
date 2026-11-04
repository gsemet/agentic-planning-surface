# Series 07 — Dynamic workflow replaces the Foreman

## Goal

Run the series 06b scenario (4 CRs, add CR-5 mid-run, change CR-2 mid-run) with a Copilot
**dynamic workflow** as the Foreman, and compare cost, quality and steering with the
session-based factory.

## Setup

| Item | Value |
|------|-------|
| Engine | `copilot --experimental workflow run factory` (CLI 1.0.105, headless) |
| Foreman | the workflow code ([kit/extension.mjs](./kit/extension.mjs), about 70 lines): no LLM |
| Driver judgement | in code: accept when the Inspector reports no blocking finding and no change arrived; otherwise one fix round (max 2) |
| Coder / Inspector | `ctx.agent(..., { agent: "coder" \| "inspector" })`, the same `gpt-5.6-luna` custom agents as series 04–06; Inspector output enforced by a JSON schema |
| Parallelism | 4 workers pulling from the inbox; `maxConcurrentSubagents: 4` |
| Steering | `inbox.json` in the lab, edited by the CoS; the workflow re-reads it between steps (no tokens) |
| Isolation | one `git worktree` per CR, created by the workflow with `execSync` |
| Lab | `/tmp/crf-labs/07` (`kit/setup.sh /tmp/crf-labs/07`) |

Command:

```bash
cd /tmp/crf-labs/07/repo
GITHUB_COPILOT_PROMPT_MODE_EXTENSIONS=true copilot --experimental --allow-all-tools \
  --add-dir /tmp/crf-labs/07 --add-dir /private/tmp/crf-labs/07 \
  workflow run factory --args '{"lab":"/tmp/crf-labs/07"}' --result-file /tmp/crf-labs/07/result.json
```

`--add-dir` is required: without it every shell call in a worktree is denied (first attempt,
aborted, $0.011).

## Checks

| # | Check | Result |
|---|-------|--------|
| W1 | 4 CRs delivered in parallel, in worktrees | **pass** |
| S1 | CR-5 added to `inbox.json` mid-run is picked up and delivered | **pass** |
| S2 | CR-2 change added mid-run is applied | **pass**: detected after round 1 (`late_change=true`), applied in round 2 (`c8a2dbd`, tie rule + `ValueError`) |
| Q1 | Inspector catches a defect and the loop fixes it | **pass**: CR-3 round 1 had no `variance()` (2 blocking findings); round 2 fixed it |
| Q2 | Tests pass on every branch | **pass**: 3, 5, 5, 4, 4 tests |
| E1 | Clean end of life | **pass**: the run returns when the inbox is `closed` and all CRs are done; no session, schedule or process left |
| C1 | Cost | **$0.028** (14 Luna subagents), plus $0.011 for the aborted first attempt |

## Results

- Duration: 11:50:24 → 11:51:35 (71 s).
- Result: `{"CR-1":{"rounds":1},"CR-2":{"rounds":2,"changes":1},"CR-3":{"rounds":2},"CR-4":{"rounds":1},"CR-5":{"rounds":1}}`.
- The session-state directory of the run contains only subagent calls: **no main-agent cost**.
  Orchestration, judgement, worktrees and steering cost zero tokens.

| Role | Model | Calls | USD |
|------|-------|------:|----:|
| 7 Coders (5 CRs + 2 fix rounds) | gpt-5.6-luna | 49 | 0.0158 |
| 7 Inspectors | gpt-5.6-luna | 24 | 0.0121 |
| Foreman, Drivers | code | 0 | 0 |
| **Total** | | | **0.0278** |

## Limits observed

- **Steering granularity**: a change is picked up only between steps (after a Coder or an
  Inspector). A running Coder cannot be steered: workflow subagents are hidden from `write_agent`.
- **No per-CR chat**: there is no Driver conversation to open and question. Progress is the run
  log, the worktrees and `getRunDetail`.
- **Judgement is a rule**: no LLM weighs whether a finding is worth a round. A smarter judge would
  be one more `ctx.agent` call, only when needed.
- **Reopen not implemented**: a change for a CR already done is ignored by this kit.
- **Experimental**: needs `--experimental`, token-based billing, and pre-granted permissions in
  headless mode (no approval prompts).

Telemetry: `results/telemetry/`, run log, result and final inbox in `results/`.
