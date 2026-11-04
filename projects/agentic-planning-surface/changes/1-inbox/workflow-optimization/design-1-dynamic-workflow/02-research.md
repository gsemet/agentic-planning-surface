---
title: What the harnesses offer for a cheaper change-request factory
subtitle: Verified research for the workflow-optimization discussion
date: 2026-10-27
---

# What the harnesses offer for a cheaper change-request factory

- **Date:** 2026-10-27
- **Status:** exploratory research, input to [03-design-sketch.md](03-design-sketch.md)
- **Follows:** [01-handoff.md](../01-handoff.md)

:::{important} How these facts were checked
Every statement below was checked against the raw text of an official source on 2026-10-27:
documentation pages downloaded as Markdown, release notes, changelogs, the installed Copilot CLI
package and the issue trackers. Search-engine summaries were not used as evidence. Anything
that could not be proven is labelled **not documented**. An open issue proves a current gap,
not a planned delivery.
:::

:::{figure} diagrams/harness-timeline.svg
:label: fig-timeline
:alt: Timeline from May to October 2026: Claude Code dynamic workflows on May 28, Copilot dynamic workflows on October 1, VS Code 1.142 on October 14, VS Code 1.143 on October 21, then the Copilot SDK v2 and workflows in the VS Code Copilot harness with no announced date.

Harness convergence. Dates come from the Claude Code changelog with the npm publish date, the
GitHub changelog and the VS Code release notes.
:::

## 1. Dynamic workflows exist on both sides

Both harnesses now run a **dynamic workflow**: a JavaScript script that orchestrates subagents.
The script holds the loop, the branching and the intermediate results. Only the final answer
reaches the conversation that started it. The two APIs share their core vocabulary: `agent`,
`parallel`, `pipeline`, `phase`, `log`, `args`, an output schema and a `label` per agent.

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} Claude Code

Since v2.1.154, published 2026-05-28
^^^
- Saved in `.claude/workflows/` or `~/.claude/workflows/`, run as `/<name>`.
- Runs in the CLI, the Desktop app, the IDE extensions, `claude -p` and the Agent SDK.
- Up to 16 concurrent agents by default, 1,000 agents per run.
- Resumable in the same session; `claude --resume` restores a stopped session's run.
- Agents that stall restart on their own; a run waits for a usage-limit reset.
:::

:::{grid-item-card} Copilot CLI, app and SDK

Public preview since 2026-10-01
^^^
- An `extension.mjs` calling `defineWorkflow`, in `~/.copilot/extensions/` or
  `.github/extensions/`.
- Runs headless with `copilot workflow run <name> --args @input.json`.
- Needs experimental mode in the CLI: `--experimental` or `/experimental on`.
- Durable run journal: `pause`, `resume(runId)`, saved results reused.
- Limits per run: concurrent agents, total agents, active time, AI credits.
:::
::::

The differences matter for a change-request factory:

| Capability | Claude Code | Copilot CLI / SDK |
| --- | --- | --- |
| Run shell commands from the script itself | No: "No direct filesystem or shell access from the workflow itself" | Yes: a workflow can "run commands, use tools, or call other services" |
| Human checkpoint inside one run | No: "No mid-run user input"; run each stage as its own workflow | Yes: `ctx.pause(key)` |
| Resume | Same session, from saved agent results | By run id, from saved step and agent results |
| Budget ceiling | No: the large-run warning is advisory | Yes: `maxAiCredits`, approximate |
| Who can launch a workflow | The main session only: the `Workflow` tool is withheld from every subagent | The session, by name or by `copilot workflow run` |
| Nested workflows | Not documented | Refused: the SDK type says "nested workflows are not supported" |
| Shared prompt cache in a fan-out | Yes: matching agents start staggered to reuse the first one's cache | Not documented |
| One-hour cache for workflow agents | Yes: `subagentPromptCacheTtl: "1h"` | No: requested in [copilot-cli#5220](https://github.com/github/copilot-cli/issues/5220) |
| Cost visible per agent | Yes: `/workflows` shows each agent's token usage | Per run only: credits used and number of subagents |
| Notification at the end of a run | Yes: the result appears in the session | Yes: "reports back when it's finished" |

:::{note} Per-agent cost on Copilot
The official Copilot views stop at the run. Per-subagent figures exist in the local session
logs (`events.jsonl`), which [copilot-session-usage](https://github.com/gsemet/copilot-session-usage)
already reads through its `subagent.started` and `subagent.completed` events.
:::

## 2. Wake-ups: `/loop` on both sides

Both harnesses can re-submit a prompt on a schedule while a session is open. Both also have a
**self-paced** mode, where the model chooses the next wake-up.

| | Claude Code | Copilot CLI | oh-my-pi |
| --- | --- | --- | --- |
| Command | `/loop` | `/every`, alias `/loop`; `/after` for one shot | `/loop` |
| Fixed interval | `/loop 5m <prompt>` | `/every 1h <prompt>` | No: it re-submits after each answer |
| Self-paced | Without an interval, a delay between one minute and one hour | Without an interval, Copilot "decides when to run the prompt again" and "stops on its own" | No |
| Bounded by a command | No | No | Yes: `--until '<cmd>'` or `--while '<cmd>'` |
| Can run a skill | Yes, if Claude may invoke it | Yes, if the command is schedulable | Not documented |
| Can run a built-in command | No: `/clear`, `/model` and the like arrive as plain text | Only a schedulable subset, such as `/review` or `/plan` | Not documented |
| Survives the session | No; restored on `--resume` | No; use cron with `copilot -p` | No: native scheduler requested in [#2763](https://github.com/can1357/oh-my-pi/issues/2763) |
| Experimental flag | No | Yes | No |

Copilot CLI also ships `/pr auto`: it "drives the pull request to green and stops". The CLI
changelog describes it as a self-paced loop paced around CI. Its sibling `/pr automerge` merges
the pull request, which the factory's rules forbid.

:::{warning} `/loop` cannot force a compaction in Claude Code
The scheduled-tasks page lists built-in commands among the prompts that "reach Claude as plain
text instead of executing". `/compact` is a built-in command. Section 3 lists the native
settings that trigger compaction instead.
:::

## 3. Cache lifetime and compaction in Claude Code

The prompt cache decides most of the cost of waiting. Claude Code picks the TTL by billing:

| Request bucket | Claude subscription, within plan usage | Usage credits, API key or cloud provider |
| --- | --- | --- |
| Main conversation | One hour | Five minutes; `promptCacheTtl: "1h"` to change it |
| Subagents, workflow agents, helpers | Five minutes; `subagentPromptCacheTtl: "1h"` to change it | Five minutes; same setting |

A keep-alive wake-up every four minutes is therefore unnecessary on Claude Code. Each tick would
also be a full turn: the whole context read again, an answer written, the history longer.

Compaction can be steered with documented settings:

| Setting | Effect |
| --- | --- |
| `autoCompactWindow`, `--autocompact`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | Context size that triggers auto-compaction, from 100,000 to 1,000,000 tokens |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Triggers auto-compaction earlier, as a percentage; cannot delay it |
| `idleCompaction`, on by default | Compacts a conversation idle for about 54 minutes, before the one-hour cache expires, above 200,000 tokens; interactive sessions only |
| `CLAUDE_CODE_IDLE_COMPACT_MIN_TOKENS` | Threshold for idle compaction, 100,000 at least |

:::{tip} When a manual `/compact` is cheap
While the cache is warm, the summary request reads the prefix from the cache. After the cache
has expired, it reprocesses the whole history uncached. Compact at a natural break, not after
a long wait.
:::

## 4. VS Code is moving to the Copilot SDK

- **VS Code 1.142, 2026-10-14.** The Copilot harness "is powered by the Copilot SDK" and runs
  in the Agent Host. VS Code is "progressively rolling it out as the default harness".
- **VS Code 1.143, 2026-10-21.** "The Copilot harness is now the default for new sessions."
  The enterprise note adds: "These controls are temporary while Local is retired."
- **Shared runtime.** The page [Choose an agent harness](https://code.visualstudio.com/docs/agents/run/agent-harnesses)
  says core behaviour is "more consistent across VS Code, GitHub Copilot CLI, and the GitHub
  Copilot app."

Targeting Copilot CLI therefore targets what VS Code will run.

:::{caution} Nested subagents and the retiring harness
The VS Code subagents page documents `chat.subagents.allowInvocationsFromSubagents`, off by
default, with "a maximum depth of five". The page places it in the section about the **Local**
harness, the one being retired. It does not say whether the Copilot harness honours it. A
factory built on workflows does not need nesting: the workflow spawns the coder and the reviewer
directly.
:::

## 5. What is coming

No public roadmap with dates was found. The last VS Code iteration plan in the tracker is the
March 2026 draft.

**Documented commitments, no date:**

- The Local harness is being retired (VS Code 1.143 release notes).
- Copilot SDK v2 with breaking API changes: tracking issue
  [copilot-sdk#2522](https://github.com/github/copilot-sdk/issues/2522), API redesign in
  [copilot-sdk#2523](https://github.com/github/copilot-sdk/issues/2523).

**Open user reports that affect the factory today:**

```{list-table}
:header-rows: 1
:widths: 30 50 20

* - Issue
  - Gap
  - State on 2026-10-27
* - [copilot-cli#5220](https://github.com/github/copilot-cli/issues/5220)
  - No one-hour prompt cache for Claude models
  - open
* - [copilot-cli#5251](https://github.com/github/copilot-cli/issues/5251)
  - Large fixed context injected in every session
  - open
* - [copilot-cli#333](https://github.com/github/copilot-cli/issues/333)
  - Fails behind corporate SSL inspection
  - open since 2025-10
* - [copilot-sdk#1889](https://github.com/github/copilot-sdk/issues/1889)
  - Custom agents in `.github/agents` ignored by the SDK
  - open
* - [copilot-sdk#2873](https://github.com/github/copilot-sdk/issues/2873)
  - SDK sessions in VS Code report a credit limit by mistake
  - open
* - [vscode#341550](https://github.com/microsoft/vscode/issues/341550)
  - Custom agent loses its tools when run as a subagent
  - open
* - [vscode#344621](https://github.com/microsoft/vscode/issues/344621)
  - Plugin agent dispatched through `task` gets no built-in tools
  - open, triage
* - [vscode#344576](https://github.com/microsoft/vscode/issues/344576)
  - Auto model selection ignores the custom agent's model
  - open, triage
* - [vscode#343263](https://github.com/microsoft/vscode/issues/343263)
  - No models in the Copilot harness under WSL
  - open
* - [vscode#343366](https://github.com/microsoft/vscode/issues/343366)
  - Two Copilot runtimes of different versions shipped
  - open
```

## 6. oh-my-pi

oh-my-pi has no saved, resumable workflow. Its `workflowz` keyword injects a prompt contract
around a persistent `eval` kernel with `agent()`, `workpool()`, `judge()` and a `budget`. The
LLM drives that kernel cell by cell. A pull request adding a real workflow tool,
[#1559](https://github.com/can1357/oh-my-pi/pull/1559), was closed without merge.

One idea is worth keeping: `workpool()` can keep workers alive, so a worker "keeps its
conversation across items". That is the question of reusing a coder between rounds.

## 7. Corrections to earlier statements

:::{note} Errata from the 2026-10-27 discussion
- Claude Code **does** have dynamic workflows. An earlier message said it did not.
- "Nested workflows refused" is proven for Copilot only. For Claude Code it is not documented.
- Per-agent cost is shown by Claude Code only; Copilot shows it per run.
- The VS Code background-agents page no longer describes Copilot CLI runs in isolated folders;
  it now describes the harnesses.
- The handoff assumed "dynamic workflows" meant `/loop`. They are two separate features.
:::

## Sources

- Claude Code: [dynamic workflows](https://code.claude.com/docs/en/workflows),
  [scheduled tasks and `/loop`](https://code.claude.com/docs/en/scheduled-tasks),
  [prompt caching](https://code.claude.com/docs/en/prompt-caching),
  [settings reference](https://code.claude.com/docs/en/settings-reference),
  [environment variables](https://code.claude.com/docs/en/env-vars),
  [changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md).
- GitHub Copilot: [dynamic workflows concept](https://docs.github.com/en/copilot/concepts/agents/dynamic-workflows),
  [using dynamic workflows](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-dynamic-workflows),
  [scheduling prompts](https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/schedule-prompts),
  [CLI command reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference),
  [changelog of 2026-10-01](https://github.blog/changelog/2026-10-01-dynamic-workflows-in-copilot-cli-and-the-copilot-app/).
  Installed package: `~/.copilot/pkg/darwin-arm64/1.0.104/` (`copilot-sdk/workflow.d.ts`,
  `changelog.json`).
- VS Code: [1.142](https://code.visualstudio.com/updates/v1_142),
  [1.143](https://code.visualstudio.com/updates/v1_143),
  [choose an agent harness](https://code.visualstudio.com/docs/agents/run/agent-harnesses),
  [subagents](https://code.visualstudio.com/docs/agents/run/subagents),
  [Agent Host blog post](https://code.visualstudio.com/blogs/2026/08/26/agent-host-architecture).
- oh-my-pi: [repository](https://github.com/can1357/oh-my-pi),
  [magic keywords](https://github.com/can1357/oh-my-pi/blob/main/docs/magic-keywords.md),
  [`/loop` definition](https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/slash-commands/builtin-modes.ts).
