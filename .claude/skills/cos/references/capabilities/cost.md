# Capability: cost

## Purpose

Report what a batch cost, by role and by CR, from measured usage.

## Who uses it

Chief of Staff; the Foreman for the budget stop.

## Commands

```bash
$COS cost --batch <batch> --by role
$COS cost --batch <batch> --by cr
$COS cost --batch <batch> --update   # Foreman, at each heartbeat: stores the total as spent_usd
```

The Foreman records its session id once with `$COS foreman transcript <id>`
(`$CLAUDE_CODE_SESSION_ID` on Claude, `$COPILOT_AGENT_SESSION_ID` on Copilot). The figures cover
that session and its subagents:

- **Claude:** the Foreman's transcript and its `subagents/`, priced in
  `scripts/cli/src/cos/costs.py`.
- **Copilot:** the billed per-call records of
  [copilot-session-usage](https://github.com/gsemet/copilot-session-usage) >= 1.0
  (`copilot-session-usage --agent cli calls`); cos does no pricing of its own. Install it with
  `uv tool install 'copilot-session-usage>=1'`, or point `COS_SESSION_USAGE` at another command.
  A call the tool could only estimate is counted and flagged in the first line.

The budget check in `$COS event` uses the last `--update`, so it lags by at most one heartbeat.
The Chief of Staff's own wakes are not in it: count them from its own session.

## Rules

- Measured, never estimated by a role: only `$COS cost` gives a figure.
- Budget: when spending reaches the brief's budget, `$COS event` returns `ask-cos budget`; the
  Foreman spawns nothing new until the Chief of Staff answers.
- Reference figures: design 5's [02-cost-detail.md](../../../../../projects/aps/changes/1-inbox/workflow-optimization/design-5-nested-session/02-cost-detail.md).

## Failure handling

`$COS cost` fails (a transcript missing, copilot-session-usage missing or older than 1.0, a call
without a price): report its line as is and give no figure. Never estimate a cost from token
counts, another tool or memory; for the Foreman, a failed `--update` is a question for the Chief
of Staff before the next spawn.
