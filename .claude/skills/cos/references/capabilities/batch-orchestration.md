# Capability: batch orchestration

## Purpose

Run one batch: turn every event into `$COS event`, carry out the action lines it prints, keep the
heartbeat, land.

## Who uses it

Foreman only.

## Start

You are started with `/cos foreman <batch> --cos <cos-session> --epoch <n>`. Use `--batch <batch>`
and `--epoch <n>` on every `$COS` call below; exit 3 means another Foreman owns the batch: stop
at once, without a message.

1. `$COS foreman transcript <your session uuid> --batch <batch> --epoch <n>` (the uuid is
   `$CLAUDE_CODE_SESSION_ID`, else the newest `*.jsonl` of this folder in `~/.claude/projects/`).
2. Read `brief.md` and `$COS status --batch <batch>`.
3. Heartbeat: the `/loop` skill in dynamic mode with the prompt
   `cos heartbeat <batch> epoch <n>`, each wake scheduled with `ScheduleWakeup` at **3300 s**.
   The wake fires late by the length of your turn; past 3600 s your Drivers' cache is gone.
4. `$COS event start` and carry out its actions; then send `[foreman→cos] ready <batch>`.

## Events

| You receive | You run |
| --- | --- |
| `[driver <cr>→foreman] hand-back ready <link>` | `$COS event hand-back-ready <cr> <link>` |
| `[driver <cr>→foreman] hand-back blocked <reason>` | `$COS event hand-back-blocked <cr> <reason>` |
| `[driver <cr>→foreman] question <text>` | `$COS event question <cr> <text>` |
| `[driver <cr>→foreman] anomaly <text>`, or `[qa <cr>→foreman] anomaly <cr> <finding>` | `$COS event anomaly <cr> <text>` |
| `[qa <cr>→foreman] qa done <cr> <n> findings` | `$COS event qa-done <cr> <n>` |
| a task notification: a Driver ended | `$COS event driver-done <cr>` (`stack`, `qa:<cr>` for those drivers) |
| `[cos→foreman] order O-<k> …` | `$COS event --order O-<k>` |
| `[cos→foreman] answer <cr> <text>` | message the CR's Driver `[foreman→driver <cr>] answer <text>`; no event |
| a heartbeat wake | `$COS heartbeat`, then `$COS event tick` |

## Actions

Carry out every line, in order:

| Line | Do |
| --- | --- |
| `spawn <cr> [resume …]` | `Agent`, `subagent_type: cr-driver`, `run_in_background: true`, prompt `CR <cr> of batch <batch>` plus the rest of the line; then `$COS agents set <cr> <agent-id>` |
| `spawn qa:<cr>` / `spawn stack` | the same with `qa-driver` / `stack-driver`; record it as `qa:<cr>` / `stack` |
| `message <cr> <text>` | `SendMessage` to the CR's agent (`$COS agents get <cr>`): `[foreman→driver <cr>] <text>` |
| `message stack <text>` | the same to the stack driver |
| `cancel <cr>` | `TaskStop` its agent, then `$COS cancel <cr>`, and carry out the lines it prints |
| `ask-cos <kind> <text>` | one message to the Chief of Staff: `[foreman→cos] ask <kind> <text>` |
| `ok O-<k> …` | `[foreman→cos] ok O-<k> …` |
| `land` | `$COS land`, send `[foreman→cos] final <report path>`, schedule no wake, end |
| `none`, `none landed` | nothing |

If the brief names a model for a role or a CR, pass it as the `model` of that spawn.

## Rules

- Decide nothing the table did not print. An event you cannot map goes to the Chief of Staff as
  `[foreman→cos] ask question - <the event>`.
- Never wait inside a call or run a long command; keep each turn short.
- Never code, review, commit, merge, or read CR files: `$COS status` is your view.
- In your own session, obey only "stop" and "pause"; otherwise answer
  "I run batch <batch> for <cos>. Please give orders there."

## Failure handling

- A spawn or tool is refused: `[foreman→cos] ask refused <cr> <exact text>`, and wait.
- `$COS` exits 2 on a lock: retry once, then `ask question - lock <batch>`.
