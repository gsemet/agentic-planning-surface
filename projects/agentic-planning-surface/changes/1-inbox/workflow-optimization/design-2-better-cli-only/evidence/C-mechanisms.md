---
title: Design 2 mechanisms — all-LLM factory with token cuts
date: 2026-10-27
scope: Claude Code (CLI/SDK), GitHub Copilot CLI/SDK 1.0.104, VS Code Copilot harness
---

# Design 2 mechanisms: what the harnesses document

Design 2 keeps every layer an LLM agent:
main session "Chief of Staff" → **Foreman** → **Driver** per CR → **Coder** / **Inspector**
(→ optional search agent under the Coder). This file checks the token-cutting levers against
official raw text only. It extends `design-1/evidence/04-mechanisms.md` (ids C1–C31, G1–G13,
V1–V4 there); facts already proven there are cited by those ids, not re-quoted.

**Method.** Raw sources fetched 2026-10-27 into `research2/docs/`:
Claude Code docs `https://code.claude.com/docs/en/<page>.md` (`cc-*.md`), Claude Code
`CHANGELOG.md` (top entry 2.1.312, `cc-CHANGELOG.md`), Claude API docs (`api-*.md`), GitHub
Docs article bodies (`gh-*.md`), the installed Copilot CLI package
`~/.copilot/pkg/darwin-arm64/1.0.104/` (`changelog.json` flattened to
`gh-cli-changelog-flat.txt`, `copilot-sdk/*.d.ts`, `definitions/*.yaml`) and raw
`microsoft/vscode-docs` (`vsc-*.md`). "Inferred" = drawn from two quoted facts.
"Not documented" = no official text found.

## 1. Matrix

| Mechanism | Claude Code | Copilot CLI / SDK | VS Code (Copilot harness) |
| --- | --- | --- | --- |
| Nesting depth (default) | 3 layers below main; env `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, no upper cap stated [CC1, CC2] | **Conflicting**: env table `4` (range 1–128), limits table `6` (max 256), config `subagents.maxDepth` `6`; changelog 1.0.71 lowered 6→4 [GH1–GH4] | Copilot harness: defers to Copilot runtime [VS1]; Local: off by default, max 5 [VS2] |
| Main→Foreman→Driver→Coder→search (4 layers) | Not at default (Coder at layer 3 loses `Agent`); fits with depth `4` [CC1, CC3] | Fits at depth 4 only if the root does not count; counting rule ambiguous [GH2] | Copilot: same as CLI (inferred from VS1); Local: yes (≤5) once enabled [VS2] |
| Per-agent model | Frontmatter `model`; Agent-tool `model` (aliases only); env default; precedence documented [CC4] | `model`, `models[]`, `modelPolicy`; per-call > settings `subagents.agents` > definition > parent [GH5, GH6] | `model` (string or list) in Copilot harness [VS3] |
| Per-agent effort | Frontmatter `effort`; Agent-tool `effort` (≥2.1.292); env `CLAUDE_CODE_EFFORT_LEVEL` wins [CC5] | `reasoningEffort` frontmatter; `subagents.agents.<name>.effortLevel` [GH5, GH6] | `reasoning-effort` (kebab-case) [VS3] |
| Subagent auto-compaction | Yes; per-agent `autoCompactWindow`; `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` applies [CC6, CC7] | Session: auto at ~80 %, block at ~95 %; SDK `infiniteSessions` thresholds; **subagents not documented** [GH7, GH8] | Not documented for Copilot harness |
| Agent tells a subagent to compact | **No documented way**: `/compact` from a subagent view acts on main [CC8] | `/compact` and RPC `history.compact` are session-level; for subagents not documented [GH9] | Not documented |
| Cache TTL per role | Global bucket setting `subagentPromptCacheTtl` / env, **or** per-definition `experimental.cacheTtl` (ranks below env and setting) [CC9, CC10] | No TTL control documented; Anthropic cache-write price = 1.25× input (5-min rate); 1-h option requested in open issue #5220 [GH10, GH11] | Not documented |
| 1-h cache write price | 2× base input (5-min: 1.25×); e.g. Opus 5.5 $8 vs $5/MTok [API1] | n/a | n/a |
| Background shell → notify waiting agent | Background subagent: yes; no time limit locally; 30 min/2 h in `-p`/SDK [CC11, CC12, C26, C27] | Session: notifications on shell/agent completion; **for subagents not documented** [GH12, G6] | Detached background shells (1.143) [V3]; subagent wake not documented |
| `Monitor` in subagents | Kept by background subagents; 5 min default, 30 min max, 10 min in `-p` [CC13] | No equivalent tool documented | Not documented |
| Self-wake (`/loop`, cron) in subagents | `ScheduleWakeup` withheld from all subagents; Cron tools only for teammates [CC14] | `/every`, `/after` are session commands, experimental; subagents not documented [GH13] | Automations start new sessions [V4] |
| Message a running agent | `SendMessage`; "mid-task course corrections"; mid-turn arrival [C1, C3, CC15] | `write_agent` "steers its active turn at the next processing opportunity" [G2] | Subagent chats read-only [V1] |
| Message an idle/finished agent (same context + cache) | Auto-resume, full history, can reuse warmed cache [C2, CC16] | Idle agent "waiting for `write_agent`" [GH14] | Local: stateless [V1] |
| Subagent → its parent | Yes; resumed agent reports to the subagent that resumed it [CC16] | Scopes `siblings`/`children` only; **parent scope not documented** [GH15] | Not documented |
| Named addressing | Names only "with agent teams enabled"; ID always works [CC17] | `agent_id` [GH15] | n/a |
| File mailbox wake | Agent-team inbox files exist (format not documented); for subagents use background Bash wait [CC18, CC11] | Detached shell + `shell_detached_completed` notification event; subagent wake not documented [GH12] | Not documented |
| Script posts into a session | Inbox socket `CLAUDE_CODE_MESSAGING_SOCKET` — session-level, not per subagent; line format not documented [CC19] | Extension `session.send()` [G11] | Not documented |
| Tool-output replacement hook | `PostToolUse` `updatedToolOutput` (all tools); hooks fire inside subagents [CC20, CC21] | `postToolUse` `modifiedResult`; `subagentStop` `modifiedResponse` [GH16, GH17] | Copilot harness shares Copilot hook format [VS4] |
| Built-in output cap | Bash inline 30 000 chars default; `bashOutputMaxChars` 4 000–128 000; `MAX_MCP_OUTPUT_TOKENS` 25 000 [CC22] | Tool output >20 KiB spilled to file; `COPILOT_LARGE_OUTPUT_THRESHOLD_BYTES` [GH18] | Not documented for Copilot harness |
| Instruction payload of a subagent | Own prompt (not CC system prompt) + task + CLAUDE.md/AGENTS.md + git status + preloaded skills + roster [CC23] | Custom subagent: **no** repo instructions by default (`include-custom-instructions`) [GH19] | Copilot harness defers to runtime [VS3] |
| Trim payload per role | `omitClaudeMd`, `tools`/`disallowedTools`, `mcpServers`, `skills`; git snapshot not per agent [CC24] | `tools`, `mcp-servers`, `include-custom-instructions: false`, `toolSearch`, `disabledSkills` [GH19, GH20] | `tools` (tool sets unsupported in Copilot harness) [VS3] |

## 2. Evidence

### Claude Code

**CC1 — Depth limit.** "By default, a subagent can spawn subagents of its own, up to three
layers below the main conversation. At the depth limit, Claude Code withholds the `Agent` tool
from every subagent except a fork, so a subagent at the limit does its delegated work itself and
returns one summary." "To change the limit, set `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` to the
number of subagent layers you want below your main conversation." "Set `1` to turn nesting off."
<https://code.claude.com/docs/en/sub-agents#let-subagents-spawn-their-own-subagents>

**CC2 — Env var.** "Number of subagent layers allowed below the main conversation (default: 3).
[…] a subagent at the third layer can't spawn further […] Accepts a positive whole number in
plain digits; anything else is ignored, so the limit can be adjusted but not removed. Requires
Claude Code v2.1.217 or later". <https://code.claude.com/docs/en/env-vars> (no upper bound stated)

**CC3 — Tools withheld (all depths).** First filter removes, "even when listed in the `tools`
field": "`Agent`, when the subagent is at the depth limit", "`AskUserQuestion`",
"`EndConversation`", "`EnterPlanMode`", "`ExitPlanMode`, unless the subagent's `permissionMode`
is `plan`", "`ScheduleWakeup`", "`WaitForMcpServers`", "`Workflow`". Background subagents keep
only "`Read`, `Grep`, `Glob`, `LSP`, `Bash`, `PowerShell`, `Edit`, `Write`, `NotebookEdit`,
`WebFetch`, `WebSearch`, `TodoWrite`, `Skill`, `ToolSearch`, `EnterWorktree`, `ExitWorktree`,
`Monitor`, `TaskStop`, `SendMessage`, and `Artifact`" plus `SubagentHandback`, and every MCP
tool. "a background subagent doesn't keep [`ListAgents`]". Concurrency: "when 20 subagents are
running in a session, spawning another […] fails". <https://code.claude.com/docs/en/sub-agents#available-tools>,
`#concurrent-subagent-limit`. Interactive nesting: "a subagent that launches background
subagents waits for their results before it finishes." (`#let-subagents-spawn-their-own-subagents`)

**CC4 — Model.** Frontmatter `model`: "`sonnet`, `opus`, `haiku`, `fable`, a full model ID such
as `claude-opus-5-5`, or `inherit`". "On an Agent tool call, that parameter takes a model alias
[…] Claude can't pass a full model ID or `inherit` on that call." Order: "1. The per-invocation
`model` parameter 2. The subagent definition's `model` frontmatter […] 3. The
`CLAUDE_CODE_SUBAGENT_MODEL` environment variable […] 4. The main conversation's model". "A
per-invocation `model` parameter also applies when the subagent is resumed". "There is no
per-subagent thinking setting." `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` makes Claude Code ignore
definition models. <https://code.claude.com/docs/en/sub-agents#choose-a-model>

**CC5 — Effort and other frontmatter.** `effort`: "Overrides the session effort level, but not
the `CLAUDE_CODE_EFFORT_LEVEL` environment variable." Agent tool: "it can also pass an `effort`
parameter for that invocation. The parameter overrides the `effort` field and stays in effect
when the subagent is resumed […] requires Claude Code v2.1.292 or later." Other fields in the
table: `tools`, `disallowedTools`, `permissionMode`, `maxTurns`, `autoCompactWindow`, `skills`,
`mcpServers`, `hooks`, `memory`, `background`, `omitClaudeMd`, `isolation`, `color`,
`initialPrompt`, `experimental`. <https://code.claude.com/docs/en/sub-agents#frontmatter-reference>,
`#choose-an-effort-level`

**CC6 — Subagent auto-compaction.** "Subagents support automatic compaction. Compaction triggers
as the subagent's own context window fills, and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` applies to
subagents as well." `autoCompactWindow`: "a token count from `100000` to `1000000`. If you set
`CLAUDE_CODE_AUTO_COMPACT_WINDOW`, the subagent uses that variable's window instead and the
field has no effect". <https://code.claude.com/docs/en/sub-agents#auto-compaction>.
**Newer changelog contradicts the doc**, 2.1.312: "Changed a subagent's `autoCompactWindow` to
lower the window set by `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, where it had no effect before; it
still never raises that window". `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`: "the variable can't raise
the threshold […] Applies to both main conversations and subagents" (env-vars).

**CC7 — Idle compaction is not a subagent lever.** Conditions include "you're in an interactive
terminal session" and "the conversation is on the one-hour prompt cache TTL"; "about 54 minutes
have passed since the last request". <https://code.claude.com/docs/en/settings-reference#idlecompaction>.
Applying it to subagents: **not documented**.

**CC8 — No manual compaction of a subagent.** "With a fork's or subagent's transcript open,
follow-up messages and skills go to that agent, and built-in commands go to your main
conversation […] `/compact`, `/clear`, and `/rewind` act on the main conversation".
<https://code.claude.com/docs/en/sub-agents#observe-and-steer-running-forks>. `/loop` prompts
cannot run built-in commands either (design-1 `02-research.md` §2).

**CC9 — TTL buckets and precedence.** Buckets: "Main conversation: your interactive turns,
non-interactive `-p` runs, and Agent SDK turns" / "Everything else: […] subagents, workflows,
in-process teammates, forks, compaction, and session titles". Precedence: "1.
`FORCE_PROMPT_CACHING_5M=1` […] 2. The bucket's environment variable 3. The bucket's setting 4.
For a subagent's requests, the `cacheTtl` value in the subagent's `experimental` frontmatter
field […] Claude Code ignores a `1h` there while your Claude subscription is using usage credits
5. `ENABLE_PROMPT_CACHING_1H=1` 6. The default". "Each control takes `5m` or `1h`".
<https://code.claude.com/docs/en/prompt-caching#choose-the-ttl-yourself>.
`subagentPromptCacheTtl` "applies to subagents, workflows, and Claude Code's own background and
helper requests, such as compaction and session titles" (settings-reference). Consequence
(inferred): a per-role TTL works only while the bucket env var and setting are **unset**.

**CC10 — Per-definition TTL.** `experimental` → "Set its `cacheTtl` key to `5m` or `1h` […]
reads the field only from subagent files. Requires Claude Code v2.1.248". Changelog 2.1.248:
"a per-agent prompt cache TTL used when no subagent TTL setting is configured".
<https://code.claude.com/docs/en/sub-agents#frontmatter-reference>

**CC11 — Background wait and its scope.** "A command that a foreground subagent started stops
when that subagent's run ends […] A command that the main conversation or a background subagent
started keeps running after a final response". In `-p`: "A command that a background subagent
started is stopped when the run exits." <https://code.claude.com/docs/en/tools-reference#when-a-background-command-stops>.
Notification: C26. Changelog 2.1.311: "Fixed background agents in auto mode that wait on their
own shells starting a new main conversation turn on every wake".

**CC12 — Time limits.** Local terminal/desktop/VS Code: "no time limit on background commands".
Unattended (`-p`, SDK, CI, cloud): "30 minutes, or the `timeout` Claude passes with
`run_in_background`, up to a maximum of 2 hours"; `-p` with a text prompt: "both defaults are 10
minutes". Raise with `BASH_DEFAULT_TIMEOUT_MS` > 1800000 and `BASH_MAX_TIMEOUT_MS` > 7200000.
<https://code.claude.com/docs/en/tools-reference#time-limit-for-background-commands>

**CC13 — Monitor.** Kept by background subagents (CC3). "Every watch Claude starts has a
deadline: 5 minutes by default, at most 30 minutes, and at most 10 minutes in a non-interactive
run given a single prompt with `-p`." "When you stop a subagent that started monitors […] those
monitors stop with it." <https://code.claude.com/docs/en/tools-reference#monitor-tool>

**CC14 — Self-wake.** `ScheduleWakeup` withheld from every subagent (CC3). "Teammates in agent
teams additionally keep the task tools and cron tools: […] `CronCreate`, `CronDelete`, and
`CronList`." (sub-agents). Background subagents keep no Cron tool (CC3 keep-list). "Tasks only
fire while Claude Code is running and idle"; "A session can hold up to 50 scheduled tasks";
recurring tasks "expire 7 days after creation". <https://code.claude.com/docs/en/scheduled-tasks>.
Whether a cron fired by a foreground subagent wakes that subagent: **not documented**.

**CC15 — Delivery timing.** Cross-session: "The receiving Claude reads the message between tool
calls during an active turn, so a running tool is never interrupted. When the receiving session
is idle, Claude Code starts a new turn" (cross-session-messaging). For subagents the exact
timing is **not documented**; changelog 2.1.277 confirms mid-turn arrival: "messages from other
agents (such as a subagent's SendMessage) that arrived mid-turn". User side: "When the agent is
writing a response, or waiting on work that can't move to the background, it keeps going and
reads your message once that finishes" (sub-agents, `Ctrl+Enter`).

**CC16 — Resume and parent links.** "When Claude sends a completed subagent a message with the
`SendMessage` tool, the subagent resumes in the background […] keeps the tool set from where the
subagent first ran and can keep reading the prompt cache the original run warmed." "A subagent
that has the `SendMessage` tool can send that message too. In an interactive session, the
resumed agent then reports back to the subagent that resumed it". "Resuming a subagent that
already finished takes a fresh slot without checking the limit". Cache: "the resumed run's first
request can read the cache the original run warmed" (prompt-caching) — only within the TTL.
Changelog 2.1.260: "Fixed a subagent that resumed another agent via SendMessage never being woken
by that agent's completion".

**CC17 — Names need agent teams.** "If you start a session with agent teams enabled, Claude can
give a subagent a name by passing a `name` parameter". "In an interactive session with agent
teams enabled, a subagent that Claude spawns from the main conversation with a `name` launches
as a teammate instead". Roster "appears only when the subagent's tools include `SendMessage` and
at least one other agent has a name". <https://code.claude.com/docs/en/sub-agents#subagent-names>

**CC18 — Team mailbox files.** "Each agent's mailbox is a JSON file at
`~/.claude/teams/{team-name}/inboxes/{agent-name}.json`. […] Entries that don't match the message
format are reported as errors and removed". <https://code.claude.com/docs/en/agent-teams>.
Entry schema: **not documented**.

**CC19 — Inbox socket is per session.** "Claude Code binds an inbox socket for each session".
Exported "to hooks and Bash commands as the `CLAUDE_CODE_MESSAGING_SOCKET` environment
variable"; auth line `{"type":"auth","token":"<token>"}`; "closes a connection that hasn't sent
a complete line within 30 seconds"; own-child messages delivered "such as a hook or Bash command
posting back to its own session's socket". <https://code.claude.com/docs/en/cross-session-messaging#the-sessions-inbox-socket>.
Message line format and routing to a subagent: **not documented**.

**CC20 — Output replacement.** `updatedToolOutput`: "Replaces the tool's output with the
provided value before it is sent to Claude. The value must match the tool's output shape". "For
built-in tools, a value that doesn't match the tool's output schema is ignored". Bash shape:
`stdout`, `stderr`, `interrupted`, `isImage`. <https://code.claude.com/docs/en/hooks#posttooluse-decision-control>.
Changelog 2.1.121: "PostToolUse hooks can now replace tool output for all tools".

**CC21 — Hooks in subagents.** "Hooks from settings files, managed policy settings, and plugins
also run inside subagents. When a subagent calls a tool, tool events such as `PreToolUse` and
`PostToolUse` fire the same configured hooks […] the input carries the `agent_id` and
`agent_type`". Frontmatter hooks run "only while that subagent is running".
<https://code.claude.com/docs/en/hooks>. Costs page: "a hook can grep for `ERROR` and return
only matching lines" (PreToolUse `updatedInput` example). <https://code.claude.com/docs/en/costs#offload-processing-to-hooks-and-skills>

**CC22 — Built-in caps.** Bash "Valid | Inline up to roughly 30,000 characters by default; past
that, the path of a file […] plus a preview of up to the first 2,000 characters"; "Failure |
Inline up to roughly 10,000 characters". `bashOutputMaxChars` "clamps the value into the range
`4000` to `128000`". `MAX_MCP_OUTPUT_TOKENS` "(default: 25000)". <https://code.claude.com/docs/en/tools-reference#output-limits>,
settings-reference, env-vars.

**CC23 — Subagent startup context.** "System prompt: the agent's own prompt plus environment
details that Claude Code appends, not the Claude Code system prompt." "CLAUDE.md files: every
level of the CLAUDE.md hierarchy the main conversation loads, including […] any `AGENTS.md`
files". "Git status: a snapshot". "Preloaded skills: full content of any skill named in the
agent's `skills` field". "Sibling roster". Not passed: output style, auto memory. "Subagents can
still invoke unlisted project, user, and plugin skills through the Skill tool". Whether the
skill listing text reaches a subagent: **not documented**.
<https://code.claude.com/docs/en/sub-agents#what-loads-at-startup>

**CC24 — Trimming controls.** `omitClaudeMd: true` loads "only the managed policy files";
"You can't change which subagents receive git status. Only Explore and Plan skip it." Session
wide: `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS`, `CLAUDE_CODE_DISABLE_CLAUDE_MDS`,
`claudeMdExcludes`, `skillListingBudgetFraction`, `skillOverrides`, `ENABLE_TOOL_SEARCH`
(defers MCP tools), `--append-subagent-system-prompt` for `-p`. Tool allow-list:
`tools` / `disallowedTools`; MCP per agent: `mcpServers`. (sub-agents, env-vars,
settings-reference, skills)

### Claude API pricing

**API1 — Cache write rates.** "Cache write tokens with a 5-minute TTL are 1.25 times the base
input tokens price. Cache write tokens with a 1-hour TTL are 2 times the base input tokens
price." Table: Opus 5.5 base $4, 5m write $5, 1h write $8, hits $0.20, output $20 /MTok; Sonnet
5.5 $2 / $2.50 / $4 / $0.10 / $10; Haiku 5.5 (≤100k) $0.10 / $0.125 / $0.20 / $0.01 / $0.50.
<https://platform.claude.com/docs/en/build-with-claude/prompt-caching> (`api-prompt-caching.md`)

### GitHub Copilot CLI / SDK

**GH1 — Env table (depth 4).** "`COPILOT_SUBAGENT_MAX_DEPTH` | Maximum subagent nesting depth
(default: `4`, range: `1`–`128`)." "`COPILOT_SUBAGENT_MAX_CONCURRENT` | Maximum concurrent
subagents per session (default: `32`, range: `1`–`256`)."
<https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference#environment-variables>

**GH2 — Limits table (depth 6).** "| Max depth | `6` | `256` |". "**Depth** counts how many agents
are nested within one another. When the depth limit is reached, the innermost agent cannot spawn
further subagents." Concurrency per plan: Free 2, Pro/Pro+ 4, Max 8, Business 16, Enterprise 32.
"Usage-based billing users can override these limits with the `subagents.maxConcurrency` and
`subagents.maxDepth` settings"; "ignored for plans that don't use usage-based billing".
(same page, `#subagent-limits`). Whether the root agent counts as depth 1: **not documented**.

**GH3 — Config reference (depth 6).** "`subagents.maxDepth` | `number` | `6` | Maximum subagent
nesting depth. Only honored for usage-based billing users […] Capped at `256`."
<https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference>

**GH4 — Changelog 1.0.71 (installed `changelog.json`).** "Lower the default maximum sub-agent
nesting depth from 6 to 4 to curb runaway recursive sub-agent delegation. Usage-based billing
users can still adjust `subagents.maxDepth` (up to 128)." 1.0.68: "Custom agents keep their tool
filters in nested subagents". Reading: GH2/GH3 are stale; current default is 4, cap 128 (GH1,
GH4) vs 256 (GH2, GH3) still conflicts.

**GH5 — Custom agent fields (CLI).** `description` (required), `include-custom-instructions`,
`infer` ("Allow auto-delegation by the main agent. Default: `true`"), `mcp-servers`, `model`
("When unset, inherits the outer agent's model. When the session model is set to `Auto` […]
subagents always inherit the resolved session model regardless of this field"), `models`,
`modelPolicy`, `name`, `reasoningEffort`, `tools` ("Default: `["*"]`"). "Model and effort are
resolved with this precedence, highest first: an explicit per-call value, the `subagents`
override in `~/.copilot/settings.json`, the agent definition's `model`/`models`/`reasoningEffort`
field, then the parent session's value." (cli-command-reference `#custom-agent-frontmatter-fields`).
GitHub.com reference marks `infer` "**Retired**. Use `disable-model-invocation` and
`user-invocable` instead" (`custom-agents-configuration`). Built-in `explore`
(`definitions/explore.agent.yaml`): `model: [gpt-5.6-luna, gpt-5.4-mini]`,
`reasoningEffort: low`.

**GH6 — Settings per agent.** "`subagents.agents` | Per-agent model configuration, keyed by agent
name. Each value is an object with optional `model`, `modelPolicy`, `effortLevel`, and
`contextTier` […] fields." (config-dir reference)

**GH7 — Session compaction.** "when your conversation reaches approximately 80% of the context
window's capacity, Copilot CLI automatically starts compacting the context in the background
[…] If the context fills to approximately 95% before compaction finishes, Copilot CLI pauses".
"you can trigger compaction manually at any time by entering the `/compact` command".
<https://docs.github.com/en/copilot/concepts/prompting-and-context/context-management>.
Subagent compaction: **not documented**.

**GH8 — SDK thresholds.** `InfiniteSessionConfig`: `backgroundCompactionThreshold` "@default
0.80", `bufferExhaustionThreshold` "@default 0.95"; provider `maxPromptTokens`: "The runtime
triggers conversation compaction before sending a request when the prompt […] would exceed this
limit." (`copilot-sdk/types.d.ts`). Changelog 1.0.85: "Add /settings options to opt in to context
management tools for agents and subagents" — setting name and behavior **not documented**.

**GH9 — Manual compaction APIs.** `HistoryCompactRequest` "Optional user-provided instructions to
focus the compaction summary"; command queue "e.g. '/compact'" (`generated/rpc.d.ts`). Scope is
the session; targeting a subagent **not documented**.

**GH10 — Pricing in AI credits.** "the total is converted into AI credits, where 1 AI credit =
$0.01 USD". "Anthropic models include a cache write cost in addition to cached input." Per
MTok: Claude Opus 5.5 input $4.00, cached $0.20, cache write $5.00, output $20.00; Sonnet 5.5
$2.00 / $0.10 / $2.50 / $10.00; Haiku 5.5 (≤100K) $0.10 / $0.01 / $0.125 / $0.50; GPT-5.6 Luna
(≤200K) $0.20 / $0.02 / $0.25 / $1.20. <https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing>.
Inferred: the Anthropic cache-write price equals the API 5-minute rate (API1), not the 1-hour
rate.

**GH11 — No TTL control.** No TTL text in the fetched GitHub docs, SDK types or changelog.
`github/copilot-cli#5220` "Option for 1-hour prompt cache TTL for Claude models (5-minute cache
expires during normal interactive use)": state OPEN, updated 2026-10-22 (`gh issue view`).

**GH12 — Shell notifications.** Hook `notification` types: "`shell_completed` | A background
(async) shell command finishes", "`shell_detached_completed` | A detached shell session
completes", "`agent_completed`", "`agent_idle` | A background agent finishes a turn and enters
idle state (waiting for `write_agent`)". <https://docs.github.com/en/copilot/reference/hooks-reference>.
Changelog 0.0.422: "Automatic notifications when background shell commands and agents
complete"; 1.0.71: "a detached command's completion notification is no longer lost". Built-in
`explore` lists `bash`, `read_bash`, `stop_bash`. Waking an idle **subagent** on shell exit:
**not documented**. Time limit in interactive mode: **not documented**;
`COPILOT_TASK_WAIT_TIMEOUT_SECONDS` "Maximum seconds `-p` […] waits for pending background agents
or shell commands to finish before exiting (default: `600`".

**GH13 — /every, /after.** "Schedule a recurring prompt […] for the current session […] Only
available in experimental mode." (cli-command-reference). Changelog 1.0.72: "Deliver scheduled
prompts as steering messages when the agent is busy"; 1.0.64: "Add /loop alias for the /every
command". Use by or for subagents: **not documented**.

**GH14 — Idle agents.** `agent_idle` (GH12); changelog 1.0.66 "Keep idle agents available after
you cancel a turn"; 1.0.92 "Messaging a running background agent now steers its active turn at
the next processing opportunity" (G2).

**GH15 — Scoped messaging.** Labels `self`, `sibling`, `child`. `write_agent` scopes:
"`"siblings"` | All visible sibling agents", "`"children"` | All child agents of the current
agent". "Use scoped messaging only from a subagent running inside a parent session with shared
sibling communication enabled. In top-level sessions, target agents with explicit `agent_id`
values instead." (cli-command-reference `#agent-communication`). A `parent` target: **not
documented**.

**GH16 — postToolUse.** "`modifiedResult` | Replacement tool result. Must have `resultType:
"success"`." Shape `{ resultType: "success"; textResultForLlm: string }`. "`modifiedResult` is
honored by both SDK programmatic hooks and command/HTTP config-file `postToolUse` hooks." Hooks
inside subagents carry `agentId`, `agentType`, `parentAgentId`. (hooks-reference)

**GH17 — subagentStop / subagentStart.** "`modifiedResponse` | **`subagentStop` only.** Replaces
the response returned to the parent". `subagentStart`: "`additionalContext` is prepended to the
subagent's first user message". "The built-in `general-purpose` agent does not emit
`subagentStart` or `subagentStop` events." (hooks-reference)

**GH18 — Large output.** "tool output larger than 20 KiB is saved to a temporary file by
default. The model receives the file path and a preview instead of the full output. This applies
to all tools". "set `COPILOT_LARGE_OUTPUT_THRESHOLD_BYTES`". (context-management)

**GH19 — Subagent instructions.** "A custom agent spawned as a subagent […] doesn't receive
repository instruction files (`copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md`) by default.
Set `include-custom-instructions: true`". "`general-purpose` subagent | Yes"; "Built-in `explore`,
`task`, and `code-review` subagents | No". "Starting a session with `--no-custom-instructions`
always takes priority". "Only the root agent can call `store_memory`". (cli-command-reference)
Whether the CLI base system prompt and tool schemas load into a custom subagent: **not
documented** (the context page lists "System instructions and tool definitions" as always
present for a session).

**GH20 — Other trims.** `toolSearch`: "Controls tool search (deferred tool loading)";
`disabledSkills`: "discovered but not loaded" (config-dir reference). `--available-tools` /
`--excluded-tools` (cli-command-reference).

### VS Code

**VS1 — Copilot harness delegation.** "The **Copilot** harness manages delegation to built-in or
custom subagents. […] For native agent behavior and configuration, see built-in and custom agents
in Copilot". "Copilot uses the native `task` tool for delegation". (`vsc-subagents.md`)

**VS2 — Local nesting.** "Local subagents cannot invoke further subagents by default. […] enable
`chat.subagents.allowInvocationsFromSubagents` (`false` by default). Nesting is limited to a
maximum depth of five." (`vsc-subagents.md`, `vsc-ai-settings.md`)

**VS3 — Agent file in the Copilot harness.** "`model` | String or array of strings | The model to
use in the Copilot harness." "`reasoning-effort` | String | Reasoning effort for the agent in the
Copilot harness: `low`, `medium`, `high`, `xhigh`, or `max`." "User-defined tool sets are
deprecated and are not supported in the Copilot harness." "`mcp-servers` […] Not used by custom
agents in VS Code." (`vsc-custom-agent-file-reference.md`). Note the field name differs from the
CLI's `reasoningEffort` (GH5).

**VS4 — Hooks.** "VS Code, the GitHub Copilot app, and Copilot CLI share this harness and its
hook format." "A `postToolUse` hook can add top-level `additionalContext`, but cannot undo an
action that has already completed." Plugin agents lose scoped hooks (vscode#341681).
(`vsc-hooks.md`). Inferred: `modifiedResult` (GH16) applies in the Copilot harness.

**VS5 — Summarization setting (Local).** "`github.copilot.chat.summarizeAgentConversationHistory.enabled`
_(Experimental)_ Automatically summarize the agent conversation history when the context window
is full. | `true`" (`vsc-ai-settings.md`); harness scope not stated.

## 3. Answers

1. **Nesting (Claude).** Default 3 layers below main (CC1). main→Foreman(1)→Driver(2)→Coder(3)
   works; the Coder's search agent (4) needs `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=4`, no
   documented cap (CC2). Withheld everywhere: `AskUserQuestion`, `ScheduleWakeup`, `Workflow`,
   plan-mode tools, `EndConversation`, `WaitForMcpServers`; `Agent` at the limit. Background
   subagents also lose Cron, Task*, `ListAgents`, `AskUserQuestion` etc. (CC3). Max 20 running
   subagents per session (CC3). Permission prompts of background subagents surface in main.
2. **Compaction (Claude).** Subagents auto-compact on their own window;
   `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` applies; per-agent `autoCompactWindow` ≥100 000
   (CC6). Doc vs 2.1.312 changelog disagree on interplay with the env window (CC6). Idle
   compaction: interactive main conversations only as documented (CC7). No way to make a
   subagent compact on demand (CC8) — rotation (finish + respawn with a `crf` brief) is the
   documented-safe path.
3. **Cache TTL (Claude).** Two buckets; subagents default 5 min even on a subscription (C7).
   `subagentPromptCacheTtl`/`CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL` set the whole "everything
   else" bucket (incl. compaction, titles). Per role: `experimental.cacheTtl` in each agent file,
   effective only when the bucket env/setting are unset; ignored on subscription usage credits
   (CC9, CC10). 1-h writes cost 2× base input vs 1.25× (API1).
4. **Model/effort (Claude).** CC4, CC5: frontmatter `model`, `effort`, `tools`,
   `disallowedTools`, `skills`, `memory`, `maxTurns`, `mcpServers`, `hooks`, `omitClaudeMd`,
   `autoCompactWindow`, `experimental.cacheTtl`, `background`, `isolation`, `permissionMode`.
   Per-call `model` (aliases only) and `effort` override frontmatter and persist on resume;
   `CLAUDE_CODE_EFFORT_LEVEL` and `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` override everything.
   Thinking is inherited, not per agent.
5. **Waiting (Claude).** A background subagent can leave a background Bash running and gets a
   notification on exit (C26); foreground subagents lose their commands at run end (CC11). No
   limit locally; `-p`/SDK 30 min default, 2 h max, raisable via env (CC12); in `-p` the
   command dies with the run. `Monitor`: kept, ≤30 min per watch (CC13). `ScheduleWakeup`,
   `/loop`: not for subagents; Cron: teammates only (CC14).
6. **Messaging (Claude).** `SendMessage` to a running subagent arrives mid-turn (exact point
   not documented for subagents; cross-session = between tool calls) (CC15). A finished
   subagent resumes in background with full history and can reuse its warm cache within TTL
   (CC16). Subagent→subagent resume reports back to the resumer (CC16). Names require agent
   teams; IDs always work (CC17). The messaging socket targets a session, not a subagent;
   message format not documented (CC19).
7. **Output trimming (Claude).** Yes: `PostToolUse` `updatedToolOutput` replaces any tool's
   output (schema-matched), and settings/plugin hooks fire inside subagents (CC20, CC21).
   Built-in caps: Bash 30 000 chars inline (4 000–128 000 via `bashOutputMaxChars`), MCP 25 000
   tokens (CC22).
8. **Instruction payload (Claude).** Own prompt (not the CC system prompt), task, full
   CLAUDE.md/AGENTS.md hierarchy, git status, preloaded skills, roster (CC23). Trim with
   `omitClaudeMd`, `tools`, `mcpServers`, `skills`; git snapshot only session-wide (CC24).
9. **Copilot.** Depth: 4 (env table, changelog 1.0.71) vs 6 (limits table, config ref); cap 128
   vs 256; settings overrides only on usage-based billing (GH1–GH4). Agent fields: `model`,
   `models`, `modelPolicy`, `reasoningEffort`, `tools`, `infer` (retired on GitHub.com),
   `mcp-servers`, `include-custom-instructions` (GH5); per-agent settings `subagents.agents`
   (GH6). Compaction: session 80 %/95 %, `/compact`; subagents not documented (GH7–GH9).
   Background shells and notifications exist at session level; subagent wake not documented
   (GH12). `write_agent` steers running / idle agents; scopes siblings/children (GH14, GH15).
   `/every`, `/after`: experimental, session-scoped; subagents not documented (GH13). Cache
   TTL: none documented, issue #5220 open (GH11). Pricing per MTok in AI credits, 1 credit =
   $0.01 (GH10). Output trimming: `postToolUse` `modifiedResult`, `subagentStop`
   `modifiedResponse`, 20 KiB spill (GH16–GH18). VS Code Copilot harness inherits these via
   the shared runtime (VS1, VS3, VS4), with `reasoning-effort` spelled differently.

## 4. Not documented

- **Claude Code:** exact delivery point of `SendMessage` inside a running *subagent* turn;
  whether a cron created by a foreground subagent fires into that subagent; any way for an
  agent to compact a subagent on demand; idle compaction for subagents; whether the skill
  listing reaches non-fork subagents; inbox-socket message line format and routing to a
  subagent; agent-team mailbox entry schema; whether `asyncRewake` hooks wake a subagent;
  an upper bound on `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`; whether nested subagents in an
  interactive session run foreground or background by default (only the waiting behaviour is
  stated); which of doc/changelog is right on `autoCompactWindow` vs
  `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (CC6).
- **Copilot CLI/SDK:** whether depth counts the root agent; the true default and cap (4/6,
  128/256); subagent compaction and its thresholds; the setting behind "context management
  tools for agents and subagents" (1.0.85); whether a background shell completion wakes an
  idle subagent; background-shell time limit in interactive mode; `/every`/`/after` for
  subagents; a `parent` messaging scope; any prompt-cache TTL or 1-hour option; whether the
  base system prompt and full tool schemas load into custom subagents.
- **VS Code (Copilot harness):** subagent depth setting (Local's `allowInvocationsFromSubagents`
  is documented only for Local); compaction controls; large-output threshold; cache TTL;
  steering subagents (chats read-only, V1).

## 5. Verdict per design-2 lever

| Lever | Claude Code | Copilot CLI / SDK | VS Code (Copilot harness) |
| --- | --- | --- | --- |
| Four-layer nesting + search leaf | **Supported** with `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=4` (CC1, CC2) | **Partly**: default 4, counting rule unclear; raising needs usage-based billing (GH1–GH4) | **Partly**: runtime-defined, not documented in VS Code (VS1) |
| Waits outside the LLM (background command + notify) | **Supported** for background subagents; unlimited locally, ≤2 h default cap in `-p`/SDK (C26, CC11, CC12) | **Partly**: session notifications documented; subagent wake not (GH12) | **Partly**: detached shells exist (V3); subagent wake not documented |
| Self-wake (`/loop`-like) per worker | **Not** for subagents (`ScheduleWakeup` withheld); teammates only via Cron (CC14) | **Not documented** for subagents; session `/every` experimental (GH13) | **Not** (automations = new sessions, V4) |
| File mailbox wakes a waiting agent | **Supported** as a pattern: background `crf mailbox wait` exits → notification (C26); native team inbox exists but schema undocumented (CC18) | **Partly**: same pattern via detached shell; wake of subagent not documented (GH12) | **Not documented** |
| Messaging between layers | **Supported**: `SendMessage` by ID, resume with history and warm cache (C1–C3, CC16); names need teams (CC17) | **Supported**: `write_agent` by `agent_id`, sibling/child scopes; parent scope undocumented (GH14, GH15) | **Not**: subagent chats read-only (V1) |
| Compaction / rotation | **Partly**: auto + per-agent `autoCompactWindow`, no on-demand compaction; rotation via fresh spawn (CC6–CC8) | **Partly**: session-level only documented; rotation via fresh `task` (GH7–GH9) | **Partly**: summarization exists, harness scope unclear (VS5) |
| Cache TTL per role | **Supported** via `experimental.cacheTtl` per agent file if bucket env/setting unset; 1 h = 2× write price (CC9, CC10, API1) | **Not**: no TTL control; 5-min-rate pricing; #5220 open (GH10, GH11) | **Not documented** |
| Model and effort per role | **Supported**: frontmatter + per-call override (CC4, CC5) | **Supported**: `model`/`models`/`modelPolicy`/`reasoningEffort` + settings (GH5, GH6) | **Supported**: `model`, `reasoning-effort` (VS3) |
| Output trimming | **Supported**: `updatedToolOutput` in subagents; Bash/MCP caps (CC20–CC22) | **Supported**: `modifiedResult`, `modifiedResponse`, 20 KiB spill (GH16–GH18) | **Partly**: shared hook format (VS4), not restated |
| Short role cards / small instruction payload | **Supported**: own prompt replaces CC system prompt; `omitClaudeMd`, `tools`, `mcpServers`; git snapshot unavoidable (CC23, CC24) | **Supported**: custom subagents skip repo instructions by default; `tools`, `mcp-servers`, `toolSearch` (GH19, GH20) | **Partly**: `tools` only; tool sets unsupported (VS3) |

## Sources

Local copies: `research2/docs/` (`cc-sub-agents.md`, `cc-tools-reference.md`,
`cc-prompt-caching.md`, `cc-settings-reference.md`, `cc-env-vars.md`, `cc-hooks.md`,
`cc-costs.md`, `cc-agent-teams.md`, `cc-cross-session-messaging.md`, `cc-scheduled-tasks.md`,
`cc-skills.md`, `cc-memory.md`, `cc-CHANGELOG.md`, `api-prompt-caching.md`,
`gh-reference-copilot-cli-reference-cli-command-reference.md`,
`gh-reference-copilot-cli-reference-cli-config-dir-reference.md`,
`gh-reference-hooks-reference.md`, `gh-concepts-prompting-and-context-context-management.md`,
`gh-reference-copilot-billing-models-and-pricing.md`, `gh-reference-custom-agents-configuration.md`,
`gh-cli-changelog-flat.txt`, `vsc-subagents.md`, `vsc-custom-agent-file-reference.md`,
`vsc-hooks.md`, `vsc-ai-settings.md`, `vsc-run-agent-harnesses.md`). Installed package:
`~/.copilot/pkg/darwin-arm64/1.0.104/` (`changelog.json`, `copilot-sdk/types.d.ts`,
`copilot-sdk/generated/rpc.d.ts`, `definitions/explore.agent.yaml`).
