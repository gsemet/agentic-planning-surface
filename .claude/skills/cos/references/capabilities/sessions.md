# Capability: sessions

## Purpose

Start, detach, find and talk to the Foreman's session on Claude Desktop.

## Who uses it

Chief of Staff (start, detach, ping); Foreman (reply to the Chief of Staff).

## Commands

Start, in the turn where the user asked, after preflight and `$COS open`:

```json
{"initiation": "user_asked", "title": "Foreman <batch> (<project>)", "name": "foreman-<batch>",
 "context": "fresh", "use_worktree": false, "model": "<models.foreman, or omit>",
 "effort": "<optional>", "permission_mode": "<the user's current mode, stated>",
 "prompt": "/cos foreman <batch> --cos <your session id> --epoch <n>",
 "background": "<content of the batch brief>"}
```

The epoch is the current one plus one (`$COS foreman get`; `1` for a new batch). Then, in the
same turn: `$COS foreman set <returned id>` (it must print that epoch) and
`detach_session(<returned id>)`; check the result says `detached`.
Find your own session id with `get_session("self")`.

Messages: `SendMessage` with `to` set to the session id. Ask for one idle notice with
`notify_when_idle: true` only when you must know the Foreman finished a turn.

## Rules

- Never start a session from a turn the user did not start (peer message, schedule, note): the
  app refuses it, and so do you.
- Detach at once: a linked Foreman wakes the Chief of Staff after every turn ($0.03–0.05 each).
- A message to a busy session waits until its turn ends: 15–54 s measured. Keep turns short.
- The Foreman cannot start sessions. Its team is subagents.

## Failure handling

- `start_session` refused: report the app's text to the user; do not retry with other settings.
- `detach_session` fails: stop the Foreman (`stop_session`), tell the user with the app's text,
  and start nothing else.
- The Foreman is not listed or does not answer a ping in about two minutes: read
  [recovery](recovery.md).
