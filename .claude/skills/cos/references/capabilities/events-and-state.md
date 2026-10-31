# Capability: events and state

## Purpose

Keep the batch state in code, so no agent has to remember or reread it.

## Who uses it

Everyone reads `$COS status`; Drivers write `$COS report`; the Foreman writes `$COS event`.

## Commands

Every command takes `--batch <batch>` (default: `$COS_BATCH`, else the latest open batch; a CR id
finds its own batch). Foreman commands also take `--epoch <n>`.

```bash
$COS status [--notes] [--json]               # one line per CR; a blocked CR shows its reason
$COS report <cr> <kind> [<note>]             # Drivers: pr-opened <link>, ci-green, ci-red <check>,
                                             #   ci-red-known, round-done "r<n> <verdict>", note
$COS event <kind> [<cr>] [<note>]            # Foreman: see batch-orchestration
$COS event --order O-<k>                     # Foreman: carry out an order
$COS order <kind> [<cr>] [--note T]          # Chief of Staff: add drop first change merged pause resume
$COS agents set|get <cr> [<agent-id>]        # Foreman: CR (or stack, qa:<cr>) → agent id
$COS heartbeat                               # Foreman: live CRs, pending orders, oldest silence
$COS add <title | @file> [--qa]              # a queued CR (the Foreman's order-add does it)
```

State lives in `<changes folder>/batches/<batch>/`: `batch.json`, `events.jsonl`, `brief.md`,
`crs/<cr>/{task.md,STATE.md,pr-body.md,scratch/}`. CR numbers are unique in the repository.

Exit codes: 0 ok, 1 usage, 2 precondition (the message says which), 3 stale Foreman epoch,
4 external tool (git, gh, a gate), 5 budget.

## Rules

- Only the CLI writes `batch.json` and `events.jsonl`. Never edit them.
- A Driver reports routine milestones with `$COS report` and does not message the Foreman for
  them. It messages the Foreman only for `hand-back`, `question` and `anomaly`.
- A state file is a record, not a channel: questions travel by message.
- Output is at most ten lines; `--json` gives everything.

## Failure handling

Exit 2 on a lock held over 30 s: retry once, then report `anomaly lock` to your parent.
Exit 3: you are a stale Foreman; stop.
