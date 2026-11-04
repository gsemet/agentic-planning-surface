# GitHub Copilot CLI — capabilities for multi-agent orchestration (late 2026)

Retrieval date for every web/GitHub source below: **2026-10-29**. The installed CLI
used for cross-checks is **v1.0.105** (changelog entry dated 2026-10-27), which is
also the latest entry in `github/copilot-cli`'s `changelog.md` as of retrieval.

Primary sources used:

- `docs.github.com` content, read directly from its source repository
  `github/docs` (branch `main`, file SHAs quoted per citation) because the
  rendered HTML pages could not be fetched from this sandbox (DNS-blocked for
  `web_fetch`); the underlying Markdown is the same content GitHub publishes.
- `github/copilot-cli` repository: `README.md` and `changelog.md`.
- Local primary evidence already collected in this evidence folder:
  `cli-help-1.0.105/*.txt` (verbatim `copilot help ...` output from the
  installed binary) and `local-telemetry-findings.md` (empirical
  `events.jsonl` inspection). These are cited as `local:<file>`.
- `github.blog` changelog was not reachable from this sandbox (see Gaps); no
  claims below depend on it exclusively.

Scope target: a **Chief of Staff** top-level session driving a long-lived
**Foreman** session, which "hires" **Driver** sessions (one per change
request, each in its own git worktree), which in turn spawn **Coder** and
**Inspector** subagents.

---

## 1. Subagents

**Built-in `task` tool and built-in agents.** The CLI ships built-in agents
dispatched through the `task` tool: `explore`, `task`, `general-purpose`,
`code-review`, `research`, `rubber-duck`, `security-review`. Each has a
default model, e.g. `code-review` → `claude-sonnet-4.6`, `explore` →
`gpt-5.6-luna`, `task` → `gpt-5.6-luna` (falls back to `claude-haiku-4.5`).
> "| `code-review` | claude-sonnet-4.6 | High signal-to-noise code review... |
> | `explore` | gpt-5.6-luna | Fast codebase exploration... Safe to run in
> parallel. |"
— `github/docs:content/copilot/reference/copilot-cli-reference/cli-command-reference.md`
("Built-in agents" table), retrieved 2026-10-29.

**Custom agents (`.agent.md`).** Defined as Markdown files with YAML front
matter, loaded from (highest to lowest priority): `~/.copilot/agents/`,
project `.github/agents/` (cwd → Git root), project `.claude/agents/`, a
directory added with `--add-dir`'s `.github/agents/`, plugin `agents/`
directories, then org/enterprise remote agents.
> "1 (highest) | User | `~/.copilot/agents/` ... 2 | Project |
> `.github/agents/`, from the current working directory upward to the Git
> root ..."
— same file, "Custom agent locations" table, retrieved 2026-10-29.

**Per-agent model selection / tool allowlists (front matter fields).**
Verified fields: `description` (required), `model`, `models` (priority
list), `modelPolicy` (`"preferred"` default vs `"required"` which refuses
dispatch rather than silently substituting), `reasoningEffort`, `tools`
(default `["*"]`), `infer` (auto-delegation on/off, default `true`),
`include-custom-instructions` (default `false`), `mcp-servers`.
> "`modelPolicy` | string | No | `\"preferred\"` (default) lets
> `model`/`models` be overridden ... `\"required\"` locks dispatch to one of
> the authored models—overrides are rejected and the picker's **Model**
> entry is disabled."
— same file, "Custom agent frontmatter fields" table, retrieved 2026-10-29.
This also documents an explicit model-precedence chain: explicit per-call
value → `subagents` override in `~/.copilot/settings.json` → the agent's own
`model`/`models`/`reasoningEffort` → parent session's value, with a
non-honorable choice falling back to the session value unless
`modelPolicy: required`.

**Delegating a focused task to a locally hosted model subagent**, keeping the
main session on a cloud model, is a documented pattern:
> "model: LOCAL-PROVIDER/LOCAL-MODEL / model-policy: required / tools:
> [\"read\", \"grep\", \"glob\", \"edit\", \"execute\"] / strict-tools-list:
> true / include-custom-instructions: true"
— `github/docs:content/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli.md`,
retrieved 2026-10-29.

**Tool allowlists (`--allow-tool`/`--deny-tool`/agent `tools:` field).**
Permission patterns use `Kind(argument)`, e.g. `shell(git:*)`,
`write(src/*.ts)`, `url(https://*.github.com)`, `MyMCP(create_issue)`; deny
always wins over allow, even under `--allow-all`.
> "Deny rules always take precedence over allow rules, even when
> `--allow-all` is set."
— `cli-command-reference.md`, "Tool permission patterns", retrieved
2026-10-29.

**Background vs synchronous subagents.** Subagents can run synchronously
(blocking the caller's turn) or in the background; background progress is
tracked with `read_agent` / the `/tasks` dialog, and the fleet-mode guidance
explicitly recommends: "Use background sub-agents for truly parallel work.
Use synchronous sub-agent calls for serialized steps or validation gates. ...
Do not dispatch a single background sub-agent; prefer a synchronous call or
batch multiple workers in parallel."
— `github/docs:content/copilot/how-tos/copilot-sdk/features/fleet-mode.md`,
"Best practices", retrieved 2026-10-29.

**Nesting depth / concurrency limits.** Two overlapping, and partly
conflicting, primary sources were found:
- `cli-command-reference.md` ("Subagent limits"):
  > "| Max depth | `6` | `256` | ... | Max concurrent | plan-based | `32` |"
  with a per-plan default concurrency table (Free/Education: 2, Pro/Pro+: 4,
  Max: 8, Business: 16, Enterprise: 32, usage-based billing: 32), overridable
  via `~/.copilot/settings.json`'s `subagents.maxConcurrency` /
  `subagents.maxDepth` (clamped to 32 / 256) for usage-based billing plans
  only.
- The same reference's environment-variable table instead states:
  > "`COPILOT_SUBAGENT_MAX_DEPTH` | Maximum subagent nesting depth (default:
  > `4`, range: `1`–`128`)." and "`COPILOT_SUBAGENT_MAX_CONCURRENT` |
  Maximum concurrent subagents per session (default: `32`, range: `1`–`256`)."
- The `changelog.md` confirms a **default-lowering change**:
  > "Lower the default maximum sub-agent nesting depth from 6 to 4 to curb
  > runaway recursive sub-agent delegation. Usage-based billing users can
  > still adjust `subagents.maxDepth` (up to 128)."
  — `github/copilot-cli:changelog.md`, entry `## 1.0.71 - 2026-07-16`.
  This confirms the **current** default depth is 4, with the `6`/`256`
  figures in the "Subagent limits" table being stale relative to the
  changelog and the env-var table in the same document (internal
  inconsistency in docs as retrieved; flagged, not resolved).

`/fleet` and parallel agents: see section-crossover above (`/fleet`, `--fleet`,
fleet mode). `/fleet` decomposes a plan into SQL-backed `todos`/`todo_deps`
rows with states `pending → in_progress → done`/`blocked`, and dispatches
one subagent per ready todo via the `task` tool.
> "CREATE TABLE todos (id TEXT PRIMARY KEY, title TEXT NOT NULL, description
> TEXT, status TEXT DEFAULT 'pending'); CREATE TABLE todo_deps (todo_id TEXT,
> depends_on TEXT, PRIMARY KEY (todo_id, depends_on));"
— `fleet-mode.md`, "How sub-agents coordinate", retrieved 2026-10-29. This is
exactly the `todos`/`todo_deps` schema already available to this session via
the `sql` tool, confirming it is the CLI's native coordination substrate
rather than a Compendium-specific addition.

**Parent notification when a background agent completes.** Two channels:
1. Generic session events: `subagent.started`, `subagent.completed`,
   `subagent.failed`, `subagent.selected`, `subagent.deselected` (SDK
   `session.on(...)`).
2. Hook events `subagentStart` and `subagentStop` (see §3), plus a
   fire-and-forget `notification` hook event that explicitly fires on
   "agent completion or idle":
   > "Fires asynchronously when the CLI emits a system notification (shell
   > completion, agent completion or idle, permission prompts, elicitation
   > dialogs). Fire-and-forget: never blocks the session."
   — `github/docs:content/copilot/reference/hooks-reference.md`, "Hook
   events" table, retrieved 2026-10-29.
3. Interactive UI: the sessions sidebar shows a steady blue `●` when
   > "The agent finished a turn while you were in another session, and you
   > have not opened it since."
   — `cli-command-reference.md`, "Session status indicators", retrieved
   2026-10-29.

**Messaging/steering a running subagent.** `write_agent` sends a message to
a running or idle agent by `agent_id`, or broadcast by `scope`
(`"siblings"`/`"children"`); `list_agents` discovers nearby agents with
relation labels `"self"`/`"sibling"`/`"child"`.
> "write_agent(scope=\"children\", message=\"Re-check your findings against
> the updated schema.\")"
— `cli-command-reference.md`, "Agent communication", retrieved 2026-10-29.
In the interactive UI, drilling into a subagent's timeline row lets you
"send it a steering message from the prompt box the same way you would the
main session" (`cli-command-reference.md:420`, retrieved 2026-10-29).
**Important scoping caveat found in the same section**: `write_agent` with
`scope` only works "from a subagent running inside a parent session with
shared sibling communication enabled. In top-level sessions, target agents
with explicit `agent_id` values instead." This bounds the
Chief-of-Staff/Foreman/Driver design: scoped broadcast messaging is a
subagent-tree feature, not a cross-top-level-session feature (see §2 for the
separate, SDK-level cross-session mechanism).

**Multi-turn subagents / nested trees.** `changelog.md` 1.0.?? entries
confirm: "Multi-turn subagents are always enabled, so you can send
follow-up messages to running agents" and the `/tasks` dialog supports
"nested tree browsing" with a toggle "Toggle showing all nested subagent
levels vs. this level's tasks only" (`cli-command-reference.md:413`,
retrieved 2026-10-29).

---

## 2. Sessions

**Session creation/messaging between sessions.** The CLI itself does not
expose a documented command that lets one *top-level* interactive session
message another independently-running top-level session; coordination
between independent sessions is an SDK/server-level capability instead. The
Copilot SDK (`@github/copilot-sdk`, Python/Go/.NET/Rust analogues) exposes a
single `CopilotClient` that can `createSession()` many named sessions against
one running CLI server, `listSessions()`, `resumeSession(id)`, `disconnect()`
and `deleteSession(id)`:
> "const sessions = await client.listSessions(); ... const repoSessions =
> await client.listSessions({ repository: \"owner/repo\" });"
— `github/docs:content/copilot/how-tos/copilot-sdk/features/session-persistence.md`,
"Listing active sessions", retrieved 2026-10-29. This is the mechanism a
Foreman process would use to programmatically spin up one Driver session per
change request and keep a registry of their session IDs — not a built-in CLI
slash command.

A **human-facing** analogue for steering a *different* session from the same
account exists (`/remote on` + `github.com/copilot/agents` or GitHub
Mobile), but this is remote *human* control of one session, not
agent-to-agent session messaging:
> "Remote control lets you connect to a running Copilot CLI session from any
> browser or from GitHub Mobile."
— `github/docs:content/copilot/how-tos/copilot-cli/use-copilot-cli/steer-remotely.md`,
retrieved 2026-10-29.

**`--resume` / `--continue` / session IDs / naming.**
> "`-r`, `--resume[=VALUE]` | Resume a previous interactive session by
> choosing from a list. Optionally specify a session ID, ID prefix, or
> session name. ... Conflicts with `--continue`." / "`--continue` | Resume
> the most recent session in the current working directory, falling back to
> the globally most recent session. Conflicts with `--resume`." /
> "`--session-id ID` | Use an exact session or task ID ... If nothing
> matches, a new session is created only when the value is a valid UUID."
— `cli-command-reference.md`, "Command-line options", retrieved 2026-10-29.
Session naming: `/rename [NAME]` (alias of `/session rename`). SDK session
IDs are caller-chosen strings (recommended pattern `user-{userId}-{taskId}`)
— `session-persistence.md`, "Session ID best practices", retrieved
2026-10-29.

**Headless `copilot -p` / non-interactive mode with JSON output.**
> "`-p PROMPT` | Execute a prompt in non-interactive mode. ... `-s` |
> Suppress stats and decoration ... `--output-format=FORMAT` | Set the
> output format: `text` (the default) or `json`. With `json`, the CLI emits
> JSONL (one JSON object per line) ..."
— `github/docs:content/copilot/reference/copilot-cli-reference/cli-programmatic-reference.md`,
retrieved 2026-10-29. A related non-interactive primitive,
`copilot workflow run WORKFLOW-NAME --output-format json`, emits a final
JSONL record `{"type":"workflow.result", "data":{"name","run":{"runId",
"status" ("completed"|"halted"|"paused"|"cancelled"|"error"), "result",
"pauseInfo"|"reason"|"error"|"failure"}, "resultFile"}}`
— same file, "Workflow output" table, retrieved 2026-10-29.

**ACP (Agent Client Protocol) server mode** — **public preview**:
> "ACP support in Copilot CLI is in public preview and subject to change." /
> "Use the `--acp` option ... You can specify the transport mode with either
> the `--stdio` or `--port` options."
— `github/docs:content/copilot/reference/copilot-cli-reference/acp-server.md`,
retrieved 2026-10-29. Server-launch options (`--available-tools`,
`--excluded-tools`, `--effort`/`--reasoning-effort`) are fixed for every
session the server creates; a connecting client cannot override them
per-session via `session/new`. `--fleet` is explicitly **not supported** in
ACP mode (`speed-up-task-completion.md`, retrieved 2026-10-29).

**`/delegate` to cloud coding agent.**
> "Offload work to run in the cloud using Copilot coding agent. ... Your
> request is sent to Copilot coding agent. The agent creates a pull request
> with the changes. You can continue working locally while the cloud agent
> works."
— `github/docs:content/copilot/how-tos/copilot-cli/cli-best-practices.md`,
"The `/delegate` command", retrieved 2026-10-29. This is a one-way hand-off
to GitHub's cloud coding agent (asynchronous PR creation), distinct from
local subagent delegation via `task`.

**Remote sessions**: `--connect[=SESSION-ID]` connects directly to an
existing remote session (conflicts with `--resume`/`--continue`); legacy
`--remote`/`--server`/`--headless` flags exist for SDK server startup only
and are not supported for interactive `-p` startup (`cli-command-reference.md`,
retrieved 2026-10-29).

**Worktree support** is a first-class CLI feature:
> "`-w`, `--worktree[=NAME]` | Create or reuse an isolated Git worktree
> under `<repo>.worktrees/` by default and start the session inside it. ...
> By default, branches off the current checkout (`HEAD`); set the
> `worktreeBaseRef` setting to `\"defaultBranch\"` to branch off the remote
> default branch instead. Conflicts with `--resume`, `--continue`, and
> `--connect`."
— `cli-command-reference.md`, retrieved 2026-10-29. Slash-command
equivalents `/worktree`, `/worktree new`, `/move`, and `/fork worktree`
exist in the interactive UI:
> "`/fork [NAME]`, `/branch [NAME]` | Fork the current session into a new
> session ... `/fork worktree` forks the current session, preserving its
> conversation context, into a new Git worktree branched off `HEAD`."
— same file, "Slash commands" table, retrieved 2026-10-29. A configurable
template controls worktree placement:
> "A `worktreePathTemplate` setting decides where `/worktree`, `/move`,
> `/new` and `--worktree` create worktrees. Set for example
> `~/src/worktrees/{repo}/{branch}` ..."
— `github/copilot-cli:changelog.md`, entry `## 1.0.87 - 2026-09-21`. The
`--worktree` flag reached general availability (no longer gated behind
experimental mode) per:
> "Use /worktree, /move, and --worktree without enabling experimental mode"
— `changelog.md`, entry `## 1.0.79 - 2026-08-10`. You can also pass a task
description directly to `/worktree` to name the branch and seed the first
prompt:
> "Pass a task to /worktree (e.g. 'fix the login redirect') to name the
> branch for that task and run the sentence as the first prompt in the new
> worktree"
— `changelog.md`, entry `## 1.0.66 - 2026-06-30`. This maps directly onto
"one Driver session per change request, each in its own git worktree."
Permission scoping note: for `--add-dir` and `--plugin-dir`, relative paths
resolve against "the session working directory (the `--resume`,
`--worktree`, or `-C` directory)" (`cli-command-reference.md`, retrieved
2026-10-29), and linked worktrees "resolve to the main repository root, so
they share permissions with the main worktree" per
`cli-config-dir-reference.md` (retrieved 2026-10-29) — i.e., multiple
Driver worktrees under one repo inherit one shared trust/permission scope,
not independent sandboxes.

---

## 3. Scheduling

**`/loop` and `/every` are aliases**, both experimental (require
`/experimental on` or `--experimental`):
> "`/loop` is an alias of `/every`. So you can enter `/loop` instead of
> `/every`, if you prefer, and the effect is the same."
— `github/docs:content/copilot/how-tos/copilot-cli/automate-copilot-cli/schedule-prompts.md`,
retrieved 2026-10-29. Syntax: `/every [INTERVAL] PROMPT` (fixed cadence,
10s–1 day) or a **self-paced** form with no interval, where the model
decides the next run time and "stops on its own once it decides there's
nothing left to watch"; `/after DELAY PROMPT` fires once. Only
self-contained commands (`/plan`, `/review`, `/research`,
`/security-review`, skills) are schedulable — `/model`, `/clear`,
`/compact`, `/permissions`, `/sandbox`, `/usage`, `/context`, `/every`,
`/after` are rejected if scheduled. Both commands are scoped to the
interactive session that created them and are restored (not restarted) on
`--resume`/`--continue`: a fixed-interval wait restarts from reopen time,
but an un-triggered `/after` keeps its original absolute target time.

**True cron-less wake-ups require an external scheduler**, since `/every`
and `/after` only run while their session stays open:
> "The `/every` and `/after` commands only run while an interactive Copilot
> CLI session is open. If you want a prompt to run on a schedule even when
> no session is active, you can run Copilot CLI from an external scheduler
> such as **cron** ... or **Task Scheduler** ..., using `copilot -p
> \"YOUR PROMPT\"`."
— same file, "Running a prompt from an external scheduler", retrieved
2026-10-29. No native CLI-internal cron syntax beyond `/every`/`/after` was
found.

**Background shell completion notifications**: the `notification` hook
event (see §1) fires on "shell completion, agent completion or idle,
permission prompts, elicitation dialogs" and is "fire-and-forget: never
blocks the session" (`hooks-reference.md`, retrieved 2026-10-29).

**Hooks — full event list** (both `camelCase` and VS Code-compatible
`PascalCase` configuration keys supported):
`sessionStart`/`SessionStart`, `sessionEnd`/`SessionEnd`,
`userPromptSubmitted`/`UserPromptSubmit`, `userPromptTransformed`,
`preToolUse`/`PreToolUse`, `postToolUse`/`PostToolUse`,
`postToolUseFailure`/`PostToolUseFailure`, `agentStop`/`Stop`,
`subagentStart`, `subagentStop`/`SubagentStop`, `errorOccurred`/
`ErrorOccurred`, `preCompact`/`PreCompact`, `permissionRequest`,
`notification`.
> "`subagentStart` | A subagent is spawned (before it runs). ... |
> `subagentStop` | A subagent completes. | Yes — can block and force
> continuation. |"
— `hooks-reference.md`, "Hook events" table, retrieved 2026-10-29.
`subagentStart` input payload includes `agentName`, `agentDisplayName`,
`transcriptPath`, and lets a hook inject `additionalContext` prepended to
the subagent's first message; `subagentStop` carries the full final
`response` text and `stopReason: "end_turn"`. Hooks inside a subagent get
extra correlation fields `agentId`/`agentType`/`parentAgentId` in every
payload. One documented exception:
> "The built-in `general-purpose` agent does not emit `subagentStart` or
> `subagentStop` events. All other built-in YAML-based agents ... and
> user-defined custom agents emit these events."
— `hooks-reference.md`, `subagentStart` section, retrieved 2026-10-29.
Cloud-agent (coding agent) execution has event-by-event behavior
differences noted in the same "Hook events" table (e.g. `notification`
never fires under cloud agent; `permissionRequest` has no effect because
tools are pre-approved there).

SDK-level typed lifecycle hooks mirror this: Node `onSubagentStart`/
`onSubagentStop`, Python/Rust `on_subagent_start`/`on_subagent_stop`, Go/
.NET `OnSubagentStart`/`OnSubagentStop`, Java `setOnSubagentStart`/
`setOnSubagentStop` (`fleet-mode.md`, "Lifecycle hooks", retrieved
2026-10-29).

---

## 4. Context & cost control

**Model selection.** Interactive `/model` (with context-tier and
reasoning-level pickers), `/config model` (sets the default), `--model=NAME`
CLI flag, `COPILOT_MODEL` env var, or `model` key in
`~/.copilot/settings.json`; precedence (highest→lowest): custom-agent
definition → `--model` → `COPILOT_MODEL` → config file → CLI default
(`cli-programmatic-reference.md`, "Model precedence", retrieved 2026-10-29).
A `fusion` pseudo-model auto-selects models/execution patterns per prompt
via `--fusion-tier standard|high|max` (`choose-a-model.md`, retrieved
2026-10-29).

**Reasoning effort.** `--effort=LEVEL`/`--reasoning-effort=LEVEL` accepts
`low`, `medium`, `high`, `xhigh`, `max` (`max` only on Anthropic models per
`cli-command-reference.md`); custom agents set a default via
`reasoningEffort:` front matter, inherited from the parent when unset.

**Auto-compaction thresholds.**
> "when your conversation reaches approximately 80% of the context window's
> capacity, Copilot CLI automatically starts compacting the context in the
> background. This leaves a buffer of approximately 20% so that tool calls
> can continue to run while compaction is in progress. If the context fills
> to approximately 95% before compaction finishes, Copilot CLI pauses
> briefly to wait for compaction to complete before continuing."
— `github/docs:content/copilot/concepts/prompting-and-context/context-management.md`,
"When compaction happens", retrieved 2026-10-29. Manual trigger: `/compact`
(cancelable with <kbd>Esc</kbd>). Compaction summarizes/discards older turns;
exact "what does not preserve" detail exists in the same doc but was not
re-quoted here for length.

**`/context` / `/usage` / token counters.**
> "The first line of the output shows the active model and the number of
> tokens currently in use out of the model's total context window capacity.
> The remainder ... shows token usage ... for: System Prompt, Custom
> Instructions, System Tools, MCP Tools, Messages, Free Space, Buffer."
— `context-management.md`, "Context usage using the `/context` command",
retrieved 2026-10-29. Large tool output (over 20 KiB by default, tunable via
`COPILOT_LARGE_OUTPUT_THRESHOLD_BYTES`) is spilled to a temp file and only a
preview/path is sent to the model context, to control token spend from huge
tool results.

**Prompt caching behaviour** is directly observable in OTel attributes and
in local `events.jsonl` records: `gen_ai.usage.cache_read.input_tokens`,
`gen_ai.usage.cache_creation.input_tokens` on both `invoke_agent` and `chat`
spans (`cli-command-reference.md`, "OpenTelemetry monitoring" → "Traces",
retrieved 2026-10-29). Local empirical confirmation (already in this
evidence folder, not re-derived here):
> "Claude prefixes expire after **5 minutes**, GPT prefixes after **30
> minutes**." and "Cache read costs 5-10 % of fresh input. Cache write
> costs 125 % of fresh input."
— `local:local-telemetry-findings.md` §§1–2 (installed CLI 1.0.105,
2026-10-29), derived from `data.usage.cacheReadTokens`/
`cacheWriteTokens`/`cacheTtlSeconds` fields in
`~/.copilot/session-state/<id>/events.jsonl`.

**OpenTelemetry.** Off by default, zero overhead; activates on
`COPILOT_OTEL_ENABLED=true`, or when `OTEL_EXPORTER_OTLP_ENDPOINT` or
`COPILOT_OTEL_FILE_EXPORTER_PATH` is set. File exporter writes JSON-lines.
Span tree per turn: `invoke_agent` (root; `INTERNAL` kind for both top-level
sessions and subagent invocations) with child `chat` (`CLIENT`) and
`execute_tool` spans. `invoke_agent` attributes include
`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`,
`gen_ai.usage.cache_read.input_tokens`,
`gen_ai.usage.cache_creation.input_tokens`, `github.copilot.turn_count`,
`github.copilot.cost` ("Per-request model multiplier used for billing. Not
a monetary value."), `github.copilot.nano_aiu` (confirmed verbatim against
`local:cli-help-1.0.105/help-monitoring.txt`, the installed binary's own
help text, which matches the docs content word-for-word).

**Log files location and format.**
> "`logs/` ... Each session creates a log file named
> `process-{timestamp}-{pid}.log`." / "`session-state/` ... Each session
> directory stores an event log (`events.jsonl`) and workspace artifacts
> (plans, checkpoints, tracked files)." / "`session-store.db` | A SQLite
> database used by the CLI for cross-session data such as checkpoint
> indexing and search."
— `github/docs:content/copilot/reference/copilot-cli-reference/cli-config-dir-reference.md`,
"Automatically managed files" section, retrieved 2026-10-29.
`events.jsonl` **does include per-request token counts and cached-token
counts**: confirmed empirically in this evidence folder —
> "Every model call writes one `session.usage_record` event to
> `~/.copilot/session-state/<session-id>/events.jsonl`. ... Key fields of
> `data.usage`: `model`, `reasoningEffort`, `isAuto` ... `inputTokens`,
> `cacheReadTokens`, `cacheWriteTokens`, `outputTokens` ...
> `copilotUsage.totalNanoAiu` ... `initiator` (`agent`, `sub-agent`,
> `user`) ... `accounting.sourceSessionId`."
— `local:local-telemetry-findings.md` §1 (installed CLI 1.0.105).
This is a stronger, directly machine-readable source than OTel for a
Foreman/Driver cost-accounting design, since it requires no OTel collector.

**Session cost/limit controls.** `--max-ai-credits <credits>` caps an
entire session (interactive or `-p`) at a minimum of 30 AI credits; the cap
is a *soft* cap evaluated only after a model response returns, and
subagents "share the same session limit as the parent session"
— `local:cli-help-1.0.105/help-limits.txt` (installed binary help text,
matches `copilot help limits`), retrieved 2026-10-29.

---

## 5. Configuration

**Config files.** `~/.copilot/settings.json` (user settings; `model`,
`effortLevel`, `subagents.maxConcurrency`, `subagents.maxDepth`,
`telemetry.headersProvider`, etc.), `.github/copilot/settings.json`
(repository settings), `.github/copilot/settings.local.json` (local
overrides), `~/.copilot/mcp-config.json`, `~/.copilot/lsp-config.json`,
`~/.copilot/providers.json` (BYOK provider/model registry),
`~/.copilot/copilot-instructions.md`. Directory root is `$HOME/.copilot`
unless `COPILOT_HOME` is set
(`github/docs:content/copilot/reference/copilot-cli-reference/cli-config-dir-reference.md`,
"User-editable files", retrieved 2026-10-29).

**Permissions.** `--allow-tool=TOOL`, `--deny-tool=TOOL`,
`--allow-all-tools`/`--allow-all-paths`/`--allow-all-urls`,
`--allow-all`/`--yolo` (equivalent to all three), `--assisted-approval`
(model-mediated safety review for non-interactive runs; "only valid for
non-interactive runs" and overrides `--allow-all-tools` but not
`--allow-all-paths`/`--allow-all-urls`) — `cli-programmatic-reference.md`,
"Using assisted permissions", retrieved 2026-10-29.
`COPILOT_ALLOW_ALL=true` additionally "trusts the working directory without
prompting, loading that directory's skills, plugins, MCP servers, and
hooks (including hooks that run shell commands)" — a meaningfully broader
grant than the other truthy spellings, which "only auto-approve tools"
(`cli-command-reference.md`, "Environment variables", retrieved
2026-10-29).

**MCP servers.** Built-in GitHub MCP server ships by default; additional
servers configured via `/mcp add` or `--additional-mcp-config=JSON`
(session-scoped), stored in `mcp-config.json`. Custom agents can declare
their own `mcp-servers:` block in front matter
(`invoke-custom-agents.md`/`cli-command-reference.md`, retrieved
2026-10-29).

**Instructions files loaded into context.** Merged from all of:
`CLAUDE.md`, `GEMINI.md`, `AGENTS.md`, `.github/instructions/**/*.instructions.md`,
`.claude/rules/**/*.md`, `.github/copilot-instructions.md` (Git root and
cwd), plus `$HOME/.copilot/copilot-instructions.md`,
`$HOME/.copilot/instructions/**/*.instructions.md`, and directories named
by `COPILOT_CUSTOM_INSTRUCTIONS_DIRS`
(`cli-command-reference.md`, "Custom instructions locations", retrieved
2026-10-29). These support `@path` imports, resolved recursively with
"cycle and size guards" (same section). **Token cost**: shown directly
under the `/context` command's "Custom Instructions" line item ("shown
only when present") — `context-management.md`, retrieved 2026-10-29 — i.e.
the CLI surfaces the exact token cost of loaded instructions per session,
but a numeric constant was not published (expected to vary by repository).
Custom-agent subagents do **not** load repository instructions by default
(`include-custom-instructions: false` default); this is a deliberate
token-cost control for delegated work
(`create-custom-agents-for-cli.md`, retrieved 2026-10-29).

---

## 6. SDK

The GitHub Copilot SDK (`@github/copilot-sdk` for TypeScript, with
Python/Go/.NET/Rust equivalents) gives a script full programmatic control:

- **Create and drive sessions**: `client.createSession({ sessionId, model })`,
  `session.sendAndWait({ prompt })`, `session.disconnect()`,
  `client.resumeSession(id)`, `client.deleteSession(id)`,
  `client.listSessions({ repository })`
  (`session-persistence.md`, retrieved 2026-10-29).
- **Set model**: `model` field at session creation; changeable mid-session,
  with documented "Auto tier persistence" and "changing model on resume"
  behavior (`session-persistence.md`, headers "Resume options" / "Example:
  changing model on resume", retrieved 2026-10-29 — not re-quoted in full
  for length).
- **Read usage/events**: `session.on((event) => {...})` subscribes to the
  generic event stream, including `subagent.started`/`subagent.completed`/
  `subagent.failed`/`subagent.selected`/`subagent.deselected`
  (`fleet-mode.md`, retrieved 2026-10-29), and `session.idle` events with
  `event.idleDurationMs` (`session-persistence.md`, "Automatic cleanup",
  retrieved 2026-10-29). A dedicated streaming-events reference document
  exists (`github/docs:content/copilot/how-tos/copilot-sdk/features/streaming-events.md`,
  44 KB, retrieved 2026-10-29) cataloguing per-event-type fields in detail;
  only summarized here for length — see Gaps.
- **Fleet mode via SDK** is **experimental**: `session.rpc.fleet.start({
  prompt })` (Node/Python/Go/.NET/Rust bindings verified in docs; no Java
  binding found) — "the binding is experimental in the generated RPC
  surface; pin both the SDK and the Copilot CLI runtime if your application
  depends on it" (`fleet-mode.md`, retrieved 2026-10-29).
- **Deployment patterns** are explicitly documented for exactly this
  Foreman/Driver shape: "Pattern 1: one CLI server per user (recommended)
  ... Complete isolation" vs "Pattern 2: shared CLI server (resource
  efficient) ... Unique session IDs per user; Application-level access
  control" (`session-persistence.md`, retrieved 2026-10-29).

---

## Gaps

- `docs.github.com` and `github.blog` could not be fetched directly by the
  `web_fetch` tool in this sandbox (DNS resolution failure for all
  external hosts, including `example.com`); `curl` from `bash` could reach
  `docs.github.com` (HTTP 301) and `api.github.com`, but full-page HTML
  conversion was not pursued once the equivalent Markdown source was found
  in `github/docs` via the GitHub MCP server. No github.blog changelog
  posts were consulted; all CLI-feature-timeline claims instead come from
  `github/copilot-cli:changelog.md`, which is more granular (daily/weekly
  entries) than github.blog's own digest posts would be.
- The **Max depth `6`/`256`** figures in `cli-command-reference.md`'s
  "Subagent limits" table conflict with the same document's
  `COPILOT_SUBAGENT_MAX_DEPTH` default of `4` (range 1–128) and with the
  changelog's explicit "Lower the default ... from 6 to 4" entry
  (`## 1.0.71 - 2026-07-16`). Treat `4` (default) / `128` (usage-based
  billing max) as authoritative; the `6`/`256` table appears stale as
  retrieved and should be re-verified against a live `copilot help limits`
  or `/subagents` output before being load-bearing for design decisions.
- `--fleet`/fleet-mode SDK bindings are explicitly marked **experimental**
  and the plugin-provided sub-agent `task(agent_type=...)` registration
  path has **no verified SDK-level registration API** — only a
  runtime-level `--plugin-dir` pattern (`fleet-mode.md`, "Limitations and
  open questions"). A production Foreman/Driver design should not assume
  SDK-stable fleet APIs without re-checking the SDK's own release notes.
  `java/src/main/java` fleet bindings were explicitly reported "not found"
  in the docs' own verification pass.
- ACP server mode is **public preview**, "subject to change"
  (`acp-server.md`). If the design relies on ACP for cross-tool
  orchestration (e.g. a non-Copilot Foreman driving Copilot CLI Drivers via
  ACP), re-verify compatibility close to implementation time.
  `--fleet` is unsupported under `--acp`, which matters if Drivers are
  meant to be ACP-controlled yet still use fleet-mode internally for their
  own Coder/Inspector subagents.
  UNVERIFIED: whether an ACP client can itself dispatch/observe subagents
  (the `acp-server.md` text mentions "ACP clients receive subagent IDs, raw
  event subscriptions, and live title, mode, command, and plan updates" in
  `changelog.md`, but the full mechanism was not read end-to-end here).
- No built-in CLI command was found for **one top-level session to message
  another independent top-level session** (as opposed to subagents within
  one session's tree, or a human remotely steering one session via
  `/remote`). The only verified mechanism for a process to own and address
  many independent Driver sessions is the **SDK**, which must be used to
  implement the Foreman (SDK session registry) rather than relying on CLI
  slash commands between separate `copilot` processes. This should be
  validated against the full `streaming-events.md` and any `session.send`
  /inter-session RPCs before finalizing the Foreman implementation,
  since only a summary of that 44 KB document was reviewed here.
- `/every`/`/after` (and `/loop` alias) remain **experimental** features
  gated by `/experimental on` or `--experimental`, and are scoped to one
  open interactive session (not durable background cron); a Foreman that
  needs guaranteed wake-ups should rely on an **external** scheduler
  invoking `copilot -p` rather than in-session `/every`, per the docs'
  own recommendation.
- Exact numeric token costs of `AGENTS.md`/`copilot-instructions.md`
  loading were not found as a published constant — only that `/context`
  surfaces it live per session. No general formula (e.g. "~X tokens per
  100 lines") was located in the sources reviewed.
- This report does not independently confirm whether linked worktrees get
  separate `session-state/` /`events.jsonl` directories from the main
  worktree (only that they "share permissions with the main worktree");
  Driver-level log/cost isolation by worktree should be verified directly
  against `~/.copilot/session-state/` layout during implementation (the
  `local-telemetry-findings.md` evidence already in this folder is a good
  starting point but was captured for a single-worktree simulation).
