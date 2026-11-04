# Series 01: VS Code Agents host primitives

Date: 2026-10-29, 10:26-10:36 (Europe/Paris). Host: VS Code Agents window, Copilot CLI 1.0.105.
Lab: throwaway git repo `/tmp/crf-lab` (copied artefacts in [results/](./results/)).
Launcher: the Chief of Staff chat (this conversation), with `create_session`, model per test.

## Goal

Check, before any design work, the four primitives design 4 depends on:

| Test | Question |
|------|----------|
| T1.1 | Can a created session itself create sessions, each in its own worktree? |
| T1.2b | Can a created session run as a custom agent with a tool allowlist? |
| T2.1 | Does `/every` exist in the VS Code host, and does it keep an Opus cache warm at 4 min? |
| T3.2 | Does an idle session wake up when its background subagent finishes? |

## Method

Each test is one session started by the Chief of Staff with `create_session`
(`workspace: /tmp/crf-lab`, `worktree: false`), on the cheapest model that can answer:

| Test | Model | Prompt (abridged) |
|------|-------|-------------------|
| T1.1 | `gpt-6-luna` | "Check you have `create_session`; create 3 sessions `T1.1 driver-N` (model gpt-6-luna, worktree true) that write `pwd` to a file" |
| T1.2b | `gpt-6-luna` | `/agent foreman` then "write a marker file; say which agent you are and how many tools you have". Agent file: [lab-kit-github/agents/foreman.agent.md](./lab-kit-github/agents/foreman.agent.md) (tools: shell only) |
| T2.1 | `claude-opus-5.5` | `/every 4m Run tick.py and reply with its output only` ([tick.py](./tick.py)) |
| T3.2 v1 | `gpt-6-luna` | "Start a background Coder (`sleep 90 && date > file`), end your turn with WAITING, write a file when notified" |
| T3.2 v2 | `gpt-6-luna` | Same, but the Coder must run `sleep 90` synchronously (initial_wait 150) |

Measurements come from `~/.copilot/session-state/<id>/events.jsonl`
(`session.usage_record`, `subagent.*`, `system.notification`, `user.message`).

## Results

| Test | Verdict | Evidence |
|------|---------|----------|
| T1.1 | **PASS** | The nested session had `create_session`, `send_message`, `delete_session`, `list_sessions`, `get_session_context`, `get_current_session`, `isolate_session`, `rename_chat`. It created 3 Drivers in 3 worktrees (`/tmp/crf-lab.worktrees/<slug>`, branches `agents/<slug>`) in about 8 s. See [results/T1.1-tools.txt](./results/T1.1-tools.txt), [results/T1.1-drivers.txt](./results/T1.1-drivers.txt) |
| T1.1 note | **Flat, not nested** | Every created chat, including those created by the nested session, is attached to the Chief of Staff's session (`ahp-session/976619a6...`). Default `relationship` is `currentSession`, which is the root session, not the caller chat |
| T1.2b | **PARTIAL** | `/agent foreman` did not switch the main session: it spawned `foreman` as a **subagent** (4 tools, 1,074 tool tokens, `gpt-6-luna` from the agent file). The main session kept 87 tools (15,056 tool tokens). A main session cannot be put on a custom agent through `create_session` |
| T2.1 | **PASS**, cache warm at 4 min | `/every` exists in the host: "Scheduled #1 every 4m". First tick fired 4 min later (09:30:55Z). Opus prefix 48,626 tokens: first tick paid a full cache write ($0.245), the follow-up call in the same tick read the cache ($0.011). Second tick (09:35:00Z) read 48,777 tokens from cache: **$0.024 per tick, about $0.36/h**. Reasoning effort was `medium`: it cannot be set through `create_session`. **No way to stop it from the host** (see series 02 finding 5); a later `/every list` created a self-paced schedule #2 by mistake and the chat then wedged on a host tool call |
| T3.2 v1 | **INVALID** | The Coder backgrounded `sleep` itself and returned in 5 s; the Driver received the completion notification inside its first turn and read it with `read_agent` |
| T3.2 v2 | **PASS** | Coder done 09:30:34Z → `system.notification` (`agent_idle`) 09:30:35Z → new Driver turn → marker written 09:30:39Z. **Wake-up latency about 5 s**, no outside message needed |

## Prefix sizes measured (tokens re-sent on every call)

| Session kind | Model | Tools | Tool tokens | Prefix |
|--------------|-------|------:|------------:|-------:|
| Main session (host default) | `gpt-6-luna` | 87 | 15,056 | about 29,000 |
| Main session (host default) | `claude-opus-5.5` | 88 | n/a | 48,626 |
| Custom-agent subagent (4 tools) | `gpt-6-luna` | 4 | 1,074 | about 2,700 |

## Cost

| Session | Cost (USD) |
|---------|-----------:|
| T1.1 Foreman stub + 3 Drivers | about 0.01 |
| T1.2b | about 0.003 |
| T3.2 v1 + v2 | about 0.01 |
| T2.1 (Opus) | 0.245 cold tick, 0.024 per warm tick |

## Consequences for design 4

1. The Foreman can hire Drivers itself (T1.1). The hierarchy is logical (who created whom),
   not structural: all chats sit under the root session.
2. Session prefixes are large and fixed by the host (29k-49k tokens). Custom agents shrink the
   prefix tenfold, but **only for subagents**. Work that needs a small prefix should run in
   custom-agent subagents; main sessions should do few calls.
3. Driver wake-up on Coder completion works (T3.2 v2), so Drivers can idle at zero cost while
   their Coder runs.
4. An Opus Foreman pays about $0.25 every time its cache goes cold. `/every 4m` is the right
   tool to keep it warm, and the user decision (R2.3) is confirmed as feasible.
