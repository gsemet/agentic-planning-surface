---
title: Talking to long-running agents at low cost
subtitle: Mechanisms in Claude Code, Copilot CLI/SDK and VS Code, checked against official sources
date: 2026-10-27
---

# Talking to long-running agents at low cost

- **Date:** 2026-10-27
- **Status:** research input to `03-design-sketch.md` (sections 3, 4, 13)
- **Question:** how can the main session act as a **Chief of Staff** that keeps talking to
  long-running workers (orchestrator, per-CR drivers) without paying for idle LLM contexts?

:::{important} Method
Every claim quotes the raw text of an official source fetched on 2026-10-27: Claude Code docs
as Markdown (`code.claude.com/docs/en/<page>.md`), the Claude Code `CHANGELOG.md`, GitHub Docs
article bodies, the files shipped in the installed Copilot CLI 1.0.104 package
(`~/.copilot/pkg/darwin-arm64/1.0.104/`: `changelog.json`, `copilot-sdk/*.d.ts`,
`copilot-sdk/docs/*.md`) and the raw `microsoft/vscode-docs` Markdown. Local copies were kept in a
session scratch folder only. "Inferred" marks a conclusion drawn from two quoted facts;
"not documented" marks a gap.
:::

## 1. Capability matrix

Evidence ids (C = Claude Code, G = GitHub Copilot CLI/SDK, V = VS Code) point to section 2.

| Mechanism | Claude Code | Copilot CLI / SDK | VS Code (Copilot harness) |
| --- | --- | --- | --- |
| Main agent messages a **running** subagent | Yes, `SendMessage`; taken as "mid-task course corrections" [C1, C3] | Yes, `write_agent`; steers the active turn [G1, G2] | Not documented; subagent chats are read-only [V1] |
| Main agent messages a **finished/idle** subagent (same context) | Yes, auto-resume in background, full history [C2, C5] | Yes, multi-turn subagents [G2] | No for Local ("stateless"); Copilot harness not documented [V1] |
| User types to a subagent directly | Yes, open its transcript; `Ctrl+Enter` delivers mid-wait [C4] | Yes, "teleport" into it from `/tasks` and steer [G3] | No, read-only chats [V1] |
| Subagent ↔ sibling messaging | Yes, sibling roster incl. `main` [C6] | Yes, `list_agents`/`write_agent` with `siblings` scope [G4] | Not documented |
| Message a **workflow** agent | Not documented; `/workflows` offers only `p`/`x`/`r`/`s` [C14] | **No**: "intentionally hidden from `read_agent` and `write_agent`" [G9] | Workflows not documented in VS Code |
| Mid-run input to a workflow | **No**: "No mid-run user input" [C13] | Checkpoint `ctx.pause(key)` + resume; "Ask you for input, if the application you're using supports it" [G7, G8] | Not documented |
| Restart one workflow agent | `r` restarts it **from the same prompt**, no transcript [C14] | Not documented (pause / cancel / resume only) [G8] | Not documented |
| Who can launch a workflow | Main session only: `Workflow` removed from every subagent [C15] | The session, by name, or `copilot workflow run`; nested refused [G7, G10] | Not documented |
| Agent teams (lead + messaging peers) | Yes, experimental, interactive only [C17–C24] | No equivalent; closest is sibling messaging [G4] | No |
| Message **another session** | Yes, cross-session `SendMessage` / `ListAgents` [C9, C10] | Not documented as a tool; sidebar is UI only [G5] | Yes, session-management tools, **each send needs your confirmation** [V2] |
| Wait with no LLM turn, woken by an event | Background Bash + notification on exit; no time limit in local interactive sessions [C26, C27] | Background shells + "Automatic notifications when background shell commands and agents complete" [G6] | Detached background shells in Copilot harness [V3] |
| Self-scheduled wake-up inside a worker | Subagents: no (`ScheduleWakeup` removed); teammates: yes (`CronCreate` kept) [C15, C25] | `/every`, `/after` per session; "steering messages when the agent is busy" [G6] | Automations (new sessions on a schedule) [V4] |
| Streaming watcher | `Monitor`, max 30 min per watch [C28] | Not documented as such | Not documented |
| External script pushes into a session | Inbox socket (`CLAUDE_CODE_MESSAGING_SOCKET`), channels (MCP, research preview) [C10, C30] | Extension process: `joinSession()` + `session.send()` [G11] | Not documented |
| Idle notice without polling | `notify_when_idle`, main conversation only, local sessions [C11] | `notifyOnComplete` for workflows [G10] | Not documented |
| 1-hour cache for workers | Opt-in `subagentPromptCacheTtl: "1h"` [C7] | No (copilot-cli#5220, see `02-research.md`) | Not documented |

## 2. Evidence

### Claude Code

**C1 — Send to a subagent.** "Claude uses the `SendMessage` tool with the agent's ID or name as
the `to` field to resume it. `SendMessage` doesn't require agent teams to be enabled; only
structured team-protocol messages such as `shutdown_request` and `plan_approval_response` do."
<https://code.claude.com/docs/en/sub-agents#resume-subagents>

**C2 — Finished subagent resumes with its cache.** "When Claude sends a completed subagent a
message with the `SendMessage` tool, the subagent resumes in the background without a new
`Agent` invocation. […] The resumed run keeps the tool set from where the subagent first ran
and can keep reading the prompt cache the original run warmed." (same URL). Changelog 2.1.290:
"Fixed resumed subagents and teammates losing their earlier thinking and prompt cache after
receiving a message mid-run".
<https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md>

**C3 — Running subagent takes course corrections.** "A subagent treats messages from the agent
that launched it as normal task direction, including mid-task course corrections, and acts on
them within its own permission settings." <https://code.claude.com/docs/en/sub-agents#resume-subagents>

**C4 — User talks to a subagent.** "With a fork's or subagent's transcript open, follow-up
messages and skills go to that agent". "To have the viewed agent read your message before the
work it's waiting on finishes, send it with `Ctrl+Enter` […] Any shell command or subagent the
agent is waiting on that can move to the background moves there and keeps running."
<https://code.claude.com/docs/en/sub-agents#observe-and-steer-running-forks>

**C5 — History and restarts.** "Resumed subagents retain their full conversation history,
including all previous tool calls, results, and reasoning." "You can resume a subagent after
restarting Claude Code by resuming the same session." A subagent stopped by the user "doesn't
auto-resume. If Claude sends it a message, the message is refused". (same URL)

**C6 — Sibling roster.** "a system reminder listing `main` and every other named agent in the
session, each a valid `to` value for `SendMessage`. […] It is a snapshot taken when the
subagent starts". <https://code.claude.com/docs/en/sub-agents#what-loads-at-startup>

**C7 — Cache after a long idle.** "Subagents fall outside the main-conversation TTL bucket, so
they get five minutes even on a subscription until you choose a longer one." "After a long
enough gap, the next request recomputes the full input and re-establishes the cache".
"Everything else: the requests Claude Code makes outside that conversation, such as subagents,
workflows, in-process teammates, forks". <https://code.claude.com/docs/en/prompt-caching#cache-lifetime>

**C8 — Waking an idle session costs a full read.** "Cross-session messages: Claude Code
delivers a message from another of your sessions as a new turn when this session sits idle,
sending your full context each time." "Scheduled tasks: a session-scoped scheduled task fires
on its interval even while the session is idle, sending your full context each time."
<https://code.claude.com/docs/en/costs#why-usage-climbs-in-a-long-session>

**C9 — Cross-session delivery.** "The receiving Claude reads the message between tool calls
during an active turn, so a running tool is never interrupted. When the receiving session is
idle, Claude Code starts a new turn with the message." "a long-running `-p` worker can receive
messages […] start it with `crossSessionInbound` set to `accept` in its `--settings` value."
<https://code.claude.com/docs/en/cross-session-messaging#message-delivery>

**C10 — Script posts into a session.** "Read this section when […] you want a script or hook to
post into a session". "Claude Code exports it to hooks and Bash commands as the
`CLAUDE_CODE_MESSAGING_SOCKET` environment variable". "A script posting to its own session's
socket can send `{"type":"auth","token":"<token>"}` as the first line". "Claude Code closes a
connection that hasn't sent a complete line within 30 seconds". The format of the message line
itself is **not documented**. <https://code.claude.com/docs/en/cross-session-messaging#the-sessions-inbox-socket>

**C11 — Idle notice.** "On its own, Claude Code subscribes without starting a turn or spending
tokens in the watched session". "Only the Claude in your main conversation can subscribe, and
only to your sessions on this machine. When Claude asks for a notice from any other target,
such as a teammate, a subagent […] Claude Code refuses the whole call". "If no notice arrives
within 12 hours, Claude Code drops the subscription".
<https://code.claude.com/docs/en/cross-session-messaging#get-a-notice-when-another-session-goes-idle>

**C12 — Background sessions (agent view).** "Each background session is a full Claude Code
conversation that keeps running without a terminal attached". `claude --bg "<prompt>"` starts
one; `claude respawn <id>` restarts it. "Finished or waiting for your next message, and
unattached for about an hour: the supervisor stops the process to free resources." "Press
`Ctrl+T` to pin a session to the top and keep its process running while idle". Other sessions
are reachable "only when it binds an inbox socket" (cross-session page).
<https://code.claude.com/docs/en/agent-view#the-supervisor-process>

**C13 — No mid-run input in workflows.** "No mid-run user input | A run pauses on its own only
for agent permission prompts and a usage-limit wait. For sign-off between stages, run each stage
as its own workflow". "No direct filesystem or shell access from the workflow itself".
<https://code.claude.com/docs/en/workflows#behavior-and-limits>

**C14 — Run controls.** Keys in `/workflows`: "`p` | Pause or resume the run", "`x` | Stop the
selected agent, or stop the whole workflow", "`r` | Restart the selected running agent". "The
new attempt starts without the stalled attempt's transcript." "An agent restarts at most five
times, counting any restart you ask for with `r`." "For a run you stopped, ask Claude to
relaunch the workflow with the same script." A failed agent "runs again, and so does every agent
the script starts after it, even ones that completed." "If you background your session or exit
Claude Code while a workflow run is in progress, the run doesn't continue on its own."
<https://code.claude.com/docs/en/workflows#manage-runs>

**C15 — Workflow and wake-ups withheld from subagents.** The first filter "removes these tools,
even when listed in the `tools` field: […] `ScheduleWakeup` […] `Workflow`". A background
subagent keeps "`Bash` […] `Monitor`, `TaskStop`, `SendMessage`". "a background subagent doesn't
keep [`ListAgents`]". <https://code.claude.com/docs/en/sub-agents#available-tools>

**C16 — Nesting.** "By default, a subagent can spawn subagents of its own, up to three layers
below the main conversation." <https://code.claude.com/docs/en/sub-agents#let-subagents-spawn-their-own-subagents>

**C17 — Agent teams.** "Agent teams are experimental and disabled by default." "One session acts
as the team lead […] Teammates work independently, each in its own context window, and
communicate directly with each other. You can also talk to any teammate directly without going
through the lead." <https://code.claude.com/docs/en/agent-teams>

**C18 — Interactive only.** "In non-interactive mode with the `-p` flag, including Agent SDK
sessions, Claude doesn't spawn teammates". (same URL, *Enable agent teams*)

**C19 — Mailbox and idle.** "Automatic message delivery: when teammates send messages, they're
delivered automatically to recipients. The lead doesn't need to poll for updates." "Idle
notifications: when a teammate finishes and stops, it automatically notifies the lead and
includes its final answer". "the teammate stays running and addressable while hidden."
(same URL, *Context and communication*)

**C20 — Shared task list.** "The lead creates tasks and teammates work through them. […] A task
can also depend on other tasks". "Agents without the Task tools coordinate through messages
instead". (same URL, *Assign and claim tasks*)

**C21 — Teammate cache.** "An in-process teammate's requests fall outside the main
conversation's cache TTL bucket, so its cache holds for five minutes by default, including on a
Claude subscription." (same URL, *Token usage*)

**C22 — Teammate brought back on message.** "When Claude messages an in-process teammate that is
no longer running, Claude Code brings it back in the same session, restores any conversation
saved for it, and gives it the message as its next prompt." (same URL)

**C23 — Team limits.** "No session resumption with in-process teammates", "One team per
session", "No nested teams: teammates cannot spawn their own teammates", "No background
subagents from in-process teammates: an in-process teammate's own subagents run in the
foreground", "Lead is fixed: the main session is the lead for its lifetime."
(same URL, *Limitations*)

**C24 — Team cost.** "Agent teams use significantly more tokens than a single session." "Shut
down teammates when their work is done. Each active teammate continues consuming tokens until it
exits or the session ends." <https://code.claude.com/docs/en/costs#agent-team-token-costs>

**C25 — Teammate tools.** "Teammates in agent teams additionally keep the task tools and cron
tools: `TaskCreate`, `TaskGet`, `TaskList`, `TaskUpdate`, `CronCreate`, `CronDelete`, and
`CronList`." <https://code.claude.com/docs/en/sub-agents#available-tools>. Changelog 2.1.183:
"Fixed background tasks started by a teammate being killed when the teammate finishes a turn".

**C26 — Zero-LLM wait in a subagent.** "A background subagent can leave a background Bash or
PowerShell command running past the end of its turn. When that command ends, Claude Code sends
the subagent a notification." <https://code.claude.com/docs/en/sub-agents#tools-permissions-and-results-of-background-subagents>

**C27 — No time limit locally.** "A local session you work in from a terminal, the desktop app,
or the VS Code extension has no time limit on background commands." For `-p`, SDK, CI and cloud:
30 minutes by default, 2 hours at most. <https://code.claude.com/docs/en/tools-reference#time-limit-for-background-commands>

**C28 — Monitor.** "Runs a command in the background and feeds each output line back to
Claude". "Every watch Claude starts has a deadline: 5 minutes by default, at most 30 minutes".
<https://code.claude.com/docs/en/tools-reference#monitor-tool>

**C29 — Scheduled tasks.** "Tasks only fire while Claude Code is running and idle." "If Claude is
busy when a task comes due, the prompt waits until the current turn ends."
<https://code.claude.com/docs/en/scheduled-tasks>

**C30 — Channels and hooks.** "A channel is an MCP server that pushes events into your running
Claude Code session". "Channels are in research preview". "custom channels aren't on the
approved allowlist. Use `--dangerously-load-development-channels` to test locally." "Events
queue into the session and are processed in order." <https://code.claude.com/docs/en/channels>,
<https://code.claude.com/docs/en/channels-reference>. Hook option `asyncRewake`: "runs in the
background and wakes Claude on exit code 2". <https://code.claude.com/docs/en/hooks>

**C31 — Workflows and teammates.** The usage-limit pause does not happen "in a Remote Control or
agent team teammate session" <https://code.claude.com/docs/en/workflows#when-a-run-hits-your-usage-limit>.
This mentions workflows in a teammate session, while C15 removes `Workflow` from subagents and
C25 says teammates follow the subagent filters plus task and cron tools. Whether a teammate can
launch a workflow is **not documented** clearly.

### GitHub Copilot CLI / SDK

**G1 — Tools.** "`write_agent` | Send a message to a running agent", "`read_agent` | Check
background agent status", "`list_agents` | List available agents".
<https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference#agent-and-task-delegation-tools>

**G2 — Changelog (installed `changelog.json`).** 1.0.5: "Send follow-up messages to background
agents with the write_agent tool for multi-turn conversations". 1.0.72: "Multi-turn subagents
are always enabled, so you can send follow-up messages to running agents". 1.0.92: "Messaging a
running background agent now steers its active turn at the next processing opportunity."
1.0.66: "Keep idle agents available after you cancel a turn". 1.0.8: "Idle subagents no longer
clutter the /tasks view — they are hidden after 2 minutes of inactivity".

**G3 — User steers a subagent.** "While drilled into a subagent's view, you can send it a
steering message from the prompt box the same way you would the main session."
<https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference#tasks-dialog-shortcuts>

**G4 — Sibling messaging.** "Use `list_agents` and `write_agent` inside custom agents to inspect
nearby agents and coordinate work in a multi-agent session." "`"sibling"` | An agent launched by
the same parent | Coordinate with peer agents through `write_agent`". "Use scoped messaging only
from a subagent running inside a parent session with shared sibling communication enabled."
(same page, *Agent communication*)

**G5 — Multiple sessions.** Sessions sidebar: "a panel docked to the left of your current
conversation for quickly switching between the sessions". "There's no inactivity timeout—a
background session sitting idle isn't stopped automatically." No agent tool to message another
session is documented. <https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/work-with-multiple-sessions>

**G6 — Waits and schedules (changelog).** 0.0.422: "Automatic notifications when background
shell commands and agents complete". 1.0.66: "Let Copilot read output from and stop detached
background shell commands". 1.0.72: "Deliver scheduled prompts as steering messages when the
agent is busy". 1.0.66: "/pr auto now starts a self-paced loop that fixes one thing per run and
paces itself around CI".

**G7 — Workflows ask and pause.** A workflow can "Ask you for input, if the application you're
using supports it" and "Pause at a checkpoint so that you can review results and resume the run
when you're ready." "Copilot runs it in the background, and reports back when it's finished."
<https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/dynamic-workflows>

**G8 — Run controls.** "In an active run, press P to pause, X to cancel the run." "Press R to
resume the run." "Canceled runs cannot be resumed."
<https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-dynamic-workflows>

**G9 — Workflow agents unreachable.** "Workflow-owned subagents are intentionally hidden from
`read_agent` and `write_agent`. Use the workflow observability APIs instead."
(`copilot-sdk/docs/workflows.md`, installed package)

**G10 — SDK workflow types.** `pause(key: string)`: "Pause this run at a durable, one-shot
checkpoint." `workflow(name, args)`: "Reject because nested workflows are not supported."
`session`: "It refuses calls that start, resume, or pause a workflow run." Run option
`notifyOnComplete`: "Whether to notify the originating session when the workflow completes."
`WorkflowAgentOptions` keys: `label`, `schema`, `model`, `reasoningEffort`, `contextTier`,
`agent`; none carries a message channel. (`copilot-sdk/workflow.d.ts`)

**G11 — Extensions push messages.** Extensions "run as separate Node.js processes"; "The
extension calls `joinSession()` which establishes a JSON-RPC connection over stdio to the CLI
and attaches to the user's current foreground session." "Use `session.send()` to
programmatically inject a new user message." (`copilot-sdk/docs/extensions.md`,
`docs/examples.md`). `MessageOptions.mode`: `"enqueue"` (default) or `"immediate"`
(`types.d.ts`).

**G12 — Experimental RPC (types only).** `session.rpc.tasks.sendMessage`: "Sends a message to a
background agent task." `tasks.startAgent`: "Starts a background agent task in the session."
Both marked `@experimental` in `generated/rpc.d.ts`; not in GitHub Docs.

**G13 — Sidekick agents.** "Sidekick agents run automatically in the background and publish
context into the session inbox." `behavior: "persistent"`: "keep the same long-lived run alive
and deliver new messages into the existing loop". Triggers documented: `user.message`,
`session.context_changed`. <https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference#sidekick-agents>

### VS Code

**V1 — Subagents.** Copilot harness: "Copilot uses the native `task` tool for delegation".
Local: "Each Local invocation is stateless: the main agent can't send follow-up messages to the
same subagent." Agents window: "Read-only subagent chats show a lock icon and don't accept
input." <https://code.visualstudio.com/docs/agents/run/subagents>

**V2 — Session-management tools.** "In sessions that use the Copilot or Claude harness, agents
can use built-in session-management tools". An agent can "Send a message to another session or
chat to start or steer a follow-up task." "Sending a message to another session always requires
your confirmation." "Burst sends are capped". <https://code.visualstudio.com/docs/agents/run/sessions/manage-sessions#coordinate-work-across-sessions>

**V3 — Background.** 1.143: "you can keep Copilot harness sessions running in the background and
access them from both the VS Code editor window and the Agents window." "the agent can start
commands that need to continue running after it responds in a detached background shell."
<https://code.visualstudio.com/updates/v1_143>. Setting `chat.requestQueuing.defaultAction`:
"`steer` signals the current request to yield." <https://code.visualstudio.com/docs/agents/reference/ai-settings>

**V4 — Automations.** "Automations run agent tasks from a saved prompt, session configuration,
and schedule." Schedules: "Manual, Hourly, Daily, or Weekly". "An automation runs one session at
a time." <https://code.visualstudio.com/docs/agents/run/automations>

## 3. Answers per question

1. **Claude, messaging running agents.** The main session reaches a running or finished
   background subagent by id or name (C1–C3) and other local sessions (C9). A workflow agent has
   no documented message path (C14). After a long idle, the recipient keeps its **full history**
   (C5), but its cache is **five minutes** by default (C7), so a wake-up after a CI run rereads
   the whole context uncached (C8). `subagentPromptCacheTtl: "1h"` covers waits under an hour.
2. **Agent teams.** Lead = main session, fixed (C23). Teammates are independent sessions with a
   mailbox and a shared task list (C19, C20). The user can talk to a teammate directly (C17).
   Five-minute cache per in-process teammate (C21). Limits: experimental, interactive only, no
   resume of in-process teammates, one team, no nested teams (C18, C23). Teammates spawn only
   foreground subagents (C23). Launching a workflow from a teammate is **not documented** (C31).
3. **Waiting without a turn.** Yes: a background subagent leaves a background Bash command
   running and is notified when it ends (C26), with no time limit in a local interactive session
   (C27). `Monitor` stops after 30 minutes at most (C28). `ScheduleWakeup` and `Workflow` are
   withheld from subagents (C15); teammates keep `CronCreate` (C25).
4. **Workflows.** No mid-run input (C13). `r` restarts an agent from its original prompt (C14).
   A stopped run is relaunched with the same script and replays completed agents from the
   journal (C14). Only the main session launches one (C15).
5. **Push mechanisms.** Inbox socket for scripts and hooks (C10), channels for MCP-based
   webhooks (research preview, C30), `asyncRewake` hooks (C30), `notify_when_idle` (C11),
   background Bash notifications (C26).
6. **Copilot CLI / SDK.** `write_agent` steers running agents and resumes idle ones (G1, G2);
   the user can steer a subagent from `/tasks` (G3). Workflow agents are hidden from
   `write_agent` (G9). Workflows pause at `ctx.pause(key)` and may ask for input where the client
   supports it (G7, G10). An extension can inject messages into the foreground session (G11).
   No cross-session messaging tool is documented (G5).
7. **VS Code.** Session-management tools list, read and message other sessions, with a
   confirmation on every send (V2). Subagent chats are read-only (V1). Workflows are not
   documented in VS Code.

## 4. Not documented

- **Claude Code:** sending a message to a workflow agent; a workflow agent calling
  `SendMessage` to `main` (inferred possible from C6 and C15, not stated for workflow agents);
  whether a teammate, in-process or split-pane, can launch a `Workflow` (C31); the cache TTL
  bucket of an agent-view background session and of a split-pane teammate (the docs name only
  "your interactive turns, non-interactive `-p` runs, and Agent SDK turns"); the message-line
  format of the inbox socket (C10); whether `SendMessage` reaches a background session whose
  process the supervisor stopped (inferred no: no socket bound until restart); whether an idle
  teammate spends tokens (the costs page says "active teammate").
- **Copilot:** a tool for messaging another session; the cache TTL or cost of waking an idle
  subagent; whether subagents receive the shell completion notifications; whether a subagent can
  start a workflow; whether `ctx.session.send()` from a workflow is supported (typed, not
  documented); `--ui-server` mode and `rpc.tasks.sendMessage` (SDK types only); "Agent Factory
  runs" and `/factories` (changelog 1.0.85 only). The default nesting depth is stated as `4`
  (`COPILOT_SUBAGENT_MAX_DEPTH`) and `6` (limits table) on the same page.
- **VS Code:** dynamic workflows in the Copilot harness; `write_agent`-style steering of
  subagents; any way to auto-approve the per-send confirmation of session messages.

## 5. Architecture options

All three keep the sketch's base: CR state in `crf`, waiting in code, the main session as
Chief of Staff. They differ in where the "talkable" LLM lives between events.

### Option A — Workflow per batch, steering through `crf` state, on-demand CR concierge

```text
Chief of Staff (main session, 1h cache)
 ├─ crf note/hold/add/restack  ──► crf state (read at every step boundary)
 ├─ Workflow crf-build (no LLM orchestrator; coder/reviewer per round)
 └─ on demand: fresh "CR concierge" subagent, primed with `crf brief <cr>` (≤2k tokens)
```

- **Flexibility kept:** every user message becomes a `crf` command the script honours at its next
  step. A re-plan, such as rebuilding a PR stack, is `x` on the run plus a relaunch with new
  `args`; completed agents replay from the journal (C14, G8). When the user wants to *discuss*
  a CR, the Chief of Staff spawns a short-lived concierge with a compact brief instead of
  keeping a driver alive.
- **Cost risk:** lowest. No idle LLM context. Risks: a relaunch reruns every agent after a failed
  one (C14); stopping a run kills a coder mid-round. On Claude the script has no shell (C13), so
  each state read costs a tiny agent call; on Copilot `ctx.step` reads it for free.
- **Fit:** Claude, yes (Chief of Staff is the only workflow launcher anyway, C15). Copilot CLI,
  yes, plus `ctx.pause` for sign-off (G10). VS Code: only once workflows reach the Copilot
  harness (not documented today).

### Option B — Reachable per-CR drivers that sleep in code

```text
Chief of Staff ──SendMessage / write_agent──► driver-<cr> (named background subagent)
                                               ├─ spawns coder, reviewer (nested, C16)
                                               └─ waits: `crf ci wait <cr>` in background Bash
                                                  → notification wakes it (C26)
```

- **Flexibility kept:** the user talks to a driver through the Chief of Staff or directly in its
  transcript (C4, G3); a driver improvises (rebuilds a stack, retries a flaky job).
- **Cost risk:** each wake-up after a wait longer than the cache TTL rereads the driver's whole
  context uncached (C7, C8). With `subagentPromptCacheTtl: "1h"` a CI wait under an hour stays
  warm, at a higher write rate. Keep drivers small: `autoCompactWindow` in their frontmatter,
  coder and reviewer as nested agents so their output never enters the driver. Driver count
  times context size times wake-ups is the bill. Illustrative arithmetic, not a measurement:
  four drivers of 60k tokens, each woken eight times a day, reread about 2M uncached tokens a
  day if every wake is cold. Agent-team variant: teammates add
  `CronCreate`, a shared task list and direct user chat (C20, C25) but are experimental,
  interactive only and lost on resume (C18, C23).
- **Fit:** Claude, yes (nesting to three layers, background Bash). Copilot CLI, yes with
  `task` + `write_agent` (G1, G2), but no one-hour cache, so every wake after five minutes is
  cold. VS Code, poor: subagent chats are read-only (V1).

### Option C — Sleeping conductor in its own session, woken by `crf` events

```text
Chief of Staff ──cross-session SendMessage──► conductor (claude --bg, pinned, C12)
                                               ├─ waits: `crf watch --next-event` (background Bash)
                                               ├─ launches Workflow crf-round per CR or batch
                                               └─ reports to Chief of Staff (SendMessage / notify_when_idle)
```

- **Flexibility kept:** the conductor is a full main session, so unlike a subagent it can launch
  workflows (C15) and judge across CRs; it reads messages between tool calls (C9); a script can
  also post to its inbox socket (C10).
- **Cost risk:** one context instead of N drivers. Each event wakes a full turn (C8). Its cache
  bucket is probably "main conversation" (one hour), but that is **not documented** for
  background sessions. The supervisor stops an unattached idle session after about an hour
  unless pinned (C12); a stopped session is unreachable by message. A running workflow does not
  survive a process restart without a relaunch (C14). Gate wake-ups: `crf watch` should emit
  only decisions (CR blocked, CI red, stack conflict), not every status change.
- **Fit:** Claude, yes (cross-session messaging, `--bg`, workflows in a background session).
  Copilot CLI, partial: no cross-session tool, so the conductor *is* the main session and an
  extension (`joinSession` + `session.send`, G11) pumps `crf` events into it. VS Code: possible
  with session-management tools, but each send needs a confirmation (V2).

### Recommendation

Start with **A** and add the on-demand concierge: it keeps "talk to a CR" without paying for an
idle context, and both harnesses support it today. Keep **B** as an opt-in per CR (a CR flagged
`interactive` gets a live driver with a one-hour cache). Prototype **C** only if cross-CR judgment
during a run proves necessary; measure its wake-up count before adopting it.

## Sources

- Claude Code: [sub-agents](https://code.claude.com/docs/en/sub-agents),
  [agent teams](https://code.claude.com/docs/en/agent-teams),
  [cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging),
  [agent view](https://code.claude.com/docs/en/agent-view),
  [workflows](https://code.claude.com/docs/en/workflows),
  [tools reference](https://code.claude.com/docs/en/tools-reference),
  [prompt caching](https://code.claude.com/docs/en/prompt-caching),
  [costs](https://code.claude.com/docs/en/costs),
  [scheduled tasks](https://code.claude.com/docs/en/scheduled-tasks),
  [channels](https://code.claude.com/docs/en/channels),
  [channels reference](https://code.claude.com/docs/en/channels-reference),
  [hooks](https://code.claude.com/docs/en/hooks),
  [run agents in parallel](https://code.claude.com/docs/en/agents),
  [changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md).
- GitHub Copilot: [CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference),
  [multiple sessions](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/work-with-multiple-sessions),
  [/fleet](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/speed-up-task-completion),
  [dynamic workflows concept](https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/dynamic-workflows),
  [using dynamic workflows](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-dynamic-workflows),
  [hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference).
  Installed package `~/.copilot/pkg/darwin-arm64/1.0.104/`: `changelog.json`,
  `copilot-sdk/workflow.d.ts`, `session.d.ts`, `types.d.ts`, `client.d.ts`,
  `generated/rpc.d.ts`, `docs/workflows.md`, `docs/extensions.md`, `docs/examples.md`.
- VS Code: [subagents](https://code.visualstudio.com/docs/agents/run/subagents),
  [manage sessions](https://code.visualstudio.com/docs/agents/run/sessions/manage-sessions),
  [sessions concept](https://code.visualstudio.com/docs/agents/concepts/sessions),
  [Agent Host](https://code.visualstudio.com/docs/agents/concepts/agent-host),
  [automations](https://code.visualstudio.com/docs/agents/run/automations),
  [AI settings](https://code.visualstudio.com/docs/agents/reference/ai-settings),
  [1.143](https://code.visualstudio.com/updates/v1_143).
