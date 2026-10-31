# Capability: cost

## Purpose

Report what a batch cost, by role and by CR, from the transcripts.

## Who uses it

Chief of Staff; the Foreman for the budget stop.

## Commands

```bash
$COS cost --batch <batch> --by role
$COS cost --batch <batch> --by cr
$COS cost --batch <batch> --update   # Foreman, at each heartbeat: stores the total as spent_usd
```

The figures come from the Foreman's transcript and its subagents' transcripts, priced in
`cli/src/cos/costs.py`. The budget check in `$COS event` uses the last `--update`, so it lags by
at most one heartbeat. The Chief of Staff's own wakes are not in it: count them from its own
session.

## Rules

- Measured, never estimated: the CLI prices the Foreman's transcript and its `subagents/`.
- Budget: when spending reaches the brief's budget, `$COS event` returns `ask-cos budget`; the
  Foreman spawns nothing new until the Chief of Staff answers.
- Reference figures: design 5's [02-cost-detail.md](../../../../../projects/aps/changes/1-inbox/workflow-optimization/design-5-nested-session/02-cost-detail.md).

## Failure handling

A transcript is missing: report the parts that could be priced and name the missing one.
