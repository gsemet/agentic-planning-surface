# Local telemetry findings (Copilot CLI 1.0.105, 2026-10-29)

Source of truth: what the installed CLI writes to disk and declares in its SDK types.
No claim here comes from marketing pages.
Reproduce with [scripts/session_cost.py](./scripts/session_cost.py).

## 1. Per-call cost is persisted, per agent

Every model call writes one `session.usage_record` event to
`~/.copilot/session-state/<session-id>/events.jsonl`.
Subagent calls carry an `agentId`; `subagent.started` maps it to a display name, model and parent.

Key fields of `data.usage`:

| Field | Use for the design |
|-------|--------------------|
| `model`, `reasoningEffort`, `isAuto` | Which tier really ran |
| `inputTokens`, `cacheReadTokens`, `cacheWriteTokens`, `outputTokens` | Token split |
| `copilotUsage.tokenDetails[].costPerBatch` | Live price per 1M tokens, in nano-AIU |
| `copilotUsage.totalNanoAiu` | Billed cost of the call (1 credit = 1e9 nano-AIU = $0.01) |
| `cacheTtlSeconds`, `cacheExpiresAt` | Cache TTL and expiry instant of this prefix |
| `availableToolCount`, `toolTokenCount` | Tool-schema overhead in the prompt |
| `initiator` (`agent`, `sub-agent`, `user`) | Who triggered the call |
| `accounting.sourceSessionId` | Session that pays |

Consequence: cost measurement needs no OTel and no `/usage` scraping.
A 60-line script gives exact per-role dollars after any run.

## 2. Observed prices (USD per 1M tokens)

Read from `costPerBatch` in real calls on this account.

| Model | Input | Cache read | Cache write | Output | Cache TTL | Tools / tool tokens |
|-------|------:|-----------:|------------:|-------:|----------:|--------------------:|
| `gpt-6-luna` | 0.10 | 0.01 | 0.125 | 0.50 | 1800 s | 1 / 182 |
| `gpt-5.6-luna` | 0.20 | 0.02 | 0.25 | 1.20 | 1800 s | 75 / 12,601 |
| `gpt-6.1-sol` | 2.00 | 0.10 | 2.50 | 10.00 | 1800 s | 60 / 22,090 |
| `claude-sonnet-5` | 2.00 | 0.20 | 2.50 | 10.00 | 300 s | 85 / 15,568 |
| `claude-sonnet-5.5` | 2.00 | 0.10 | 2.50 | 10.00 | 300 s | 30 / 16,741 |
| `claude-opus-5.5` | 4.00 | 0.20 | 5.00 | 20.00 | 300 s | 88 / 18,183 |

Facts that drive the design:

- Cache read costs 5-10 % of fresh input. Cache write costs 125 % of fresh input.
- Claude prefixes expire after **5 minutes**, GPT prefixes after **30 minutes**.
- The cheapest tier is 40x cheaper than Opus on input and output.
- Tool schemas alone cost 12k-22k tokens per call, unless the tool set is trimmed
  (`gpt-6-luna` with 1 tool: 182 tokens).

## 3. Cost of the five-Driver simulation (`foreman-sim-1`)

Session `6f963b60-24f4-410a-9435-4a253a25c4e7`, 77 model calls, total **$2.28**.

| Role | Model | Calls | Input tokens | Cost |
|------|-------|------:|-------------:|-----:|
| Foreman (main) | claude-opus-5.5 | 13 | 811,342 | $0.50 |
| 5 Drivers | claude-opus-5.5 | 46 | 2,093,738 | $1.76 |
| 5 Coders | gpt-5.6-luna | 10 | 223,473 | $0.011 |
| 5 Inspectors | gpt-5.6-luna | 8 | 179,164 | $0.004 |

Lessons:

1. **Orchestration was 99 % of cost; the actual work was 1 %.**
   Drivers were general-purpose agents that inherited the Opus parent model.
2. Every Opus call re-sent about 45k tokens of prefix (system prompt plus 88 tool schemas).
   Even at 91 % cache hit, the prefix dominates.
3. Each Driver paid about 47k cache-write tokens just to start. A fresh context is not free.
4. Coder and Inspector on `gpt-5.6-luna` cost about $0.001 per call.
   Small models are cheap enough to run an Inspector on every task.

Design rule derived: **orchestrators must be code or the cheapest model, never the frontier
model; frontier models are an escalation target only.**

## 4. Steering and notification behaviour (VS Code agent host)

Measured in the same run:

| Mechanism | Latency observed | Note |
|-----------|-----------------|------|
| `send_message` mode `queue` to a busy Foreman | about 3 min 40 s | Waits until the turn ends; the turn stays open while background agents run |
| `send_message` mode `steer`, status request | a few seconds | Delivered at the next tool-call boundary |
| `send_message` mode `steer`, cancel one Driver | about 2 min | Arrived after the batch finished; useless as a kill switch |
| Completion notification to the parent chat | none | The parent must poll state |

SDK equivalent: `session.send({ mode: "enqueue" | "immediate" })`.
`immediate` interjects into the in-progress turn.

## 5. Programmatic surfaces in the installed SDK

From `copilot-sdk/generated/rpc.d.ts` and `copilot-sdk/docs/workflows.md`:

- **Sessions**: create, resume, fork, `send` (with `wait`, `mode`, `responseFormat`, `billable`),
  `sendMessages`, `cancelAllBackgroundAgents`.
- **Model control per session**: `model.switchTo`, `switchAutoTier`, `setReasoningEffort`,
  `setAllowedModels`.
- **Tasks (subagents and shells)**: `startAgent`, `list`, `getProgress`, `readOutput`,
  `sendMessage`, `cancel`, `waitForPending`.
- **Fleet**: `fleet.start`.
- **Subagent defaults**: `tools.getSubagentSettings` and `updateSubagentSettings`
  (model, effort, context tier per agent).
- **Dynamic workflows** (experimental): `workflow.run`, `resume`, `pause`, `cancel`,
  `getRunProgress`, `agent`, plus a journal. Nested workflows are not supported.
  Workflow subagents cannot be messaged.
- **Context**: `history.compact`, `metadata.getContextHeaviestMessages`.
- **Prices**: `models.listTokenPriceUnits`.
- **Agent registry**: `agentRegistry.spawn` (experimental managed child servers).

Scheduling exists but is **experimental and session-scoped** (from the local `changelog.json`):
`/every` and `/after` (alias `/loop`) schedule prompts or slash commands with natural language
or cron expressions; a Schedule Manager lists and removes them; `/pr auto` uses the same loop.
`/every` is hidden from the help output and listed under `/experimental`.
There is no SDK RPC for schedules; durable wake-ups across process restarts still need an
external process.

Subagent nesting: default max depth **4** (lowered from 6), adjustable with
`subagents.maxDepth` or `COPILOT_SUBAGENT_MAX_DEPTH` up to 128 on usage-based billing.
Default max concurrency 32 per session.
