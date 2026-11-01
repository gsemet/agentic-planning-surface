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
   `$CLAUDE_CODE_SESSION_ID` on Claude, `$COPILOT_AGENT_SESSION_ID` on Copilot). The variable is
   empty: you are `blocked`; never guess the uuid from files.
2. Read `brief.md` and `$COS status --batch <batch>`.
3. Heartbeat: its interval is the `heartbeat:` line of `$COS models get foreman` (per host,
   just under the prompt-cache TTL of the host's Claude models: `55m` on Claude Code, `4m` on
   Copilot, where that cache lives 5 minutes).
   - Claude Code: the `/loop` skill in dynamic mode with the prompt
     `cos heartbeat <batch> epoch <n>`, each wake scheduled with `ScheduleWakeup` at that interval.
   - Copilot: you arm nothing (the model tool that schedules a wake is not available). The Chief
     of Staff arms `/every <interval> cos heartbeat <batch> epoch <n>` in your chat after your
     `ready`. No wake arrives: you are `blocked`; never invent another timer.
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

Carry out every line, in order. Tool names differ per host; a tool the table does not name for
your host does not exist: the action is refused, never replaced.

| Generic | Claude Code | Copilot |
| --- | --- | --- |
| Spawn a Driver | `Agent`, `run_in_background: true` | `task`, `mode: background`, `agent_type: <role>` |
| Message a Driver | `SendMessage` to the agent id | `write_agent` to the agent id |
| Message the Chief of Staff | `SendMessage` to its session id | `send_message` to its session link |
| Stop a Driver | `TaskStop` | none: `write_agent` `[foreman→driver <cr>] stop`, it ends at its next turn |

| Line | Do |
| --- | --- |
| `spawn <cr> [resume …]` | spawn `cr-driver` in the background, prompt `CR <cr> of batch <batch>` plus the rest of the line; then `$COS agents set <cr> <agent-id>` |
| `spawn qa:<cr>` / `spawn stack` | the same with `qa-driver` / `stack-driver`; record it as `qa:<cr>` / `stack` |
| `message <cr> <text>` | message the CR's agent (`$COS agents get <cr>`): `[foreman→driver <cr>] <text>` |
| `message stack <text>` | the same to the stack driver |
| `cancel <cr>` | stop its agent, then `$COS cancel <cr>`, and carry out the lines it prints |
| `ask-cos <kind> <text>` | one message to the Chief of Staff: `[foreman→cos] ask <kind> <text>` |
| `ok O-<k> …` | `[foreman→cos] ok O-<k> …` |
| `land` | `$COS land`, send `[foreman→cos] final <report path>`, schedule no wake, end. On Copilot a wake may still come: answer `landed` with no tool call |
| `none`, `none landed` | nothing |

Before each spawn, run `$COS models get <role> --cr <cr>` and do exactly what it prints:
`model: omit` passes no `model`; `model: <id>` passes that id, character for character
([models](models.md)).

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
