# GitHub Copilot billing as of late 2026 — primary-source research

Retrieval date for all sources below: 2026-10-29, unless a different access date is
noted inline. All URLs were fetched directly (docs.github.com, github.blog,
code.visualstudio.com) on that date.

## 0. Headline verification of the user's claim

CONFIRMED, with an exact date and mechanism that **matches** the user's statement almost
exactly (the actual cut-over date is **June 1, 2026**, not "around June 2026" loosely —
it is precisely documented and repeatedly cross-referenced).

- Primary announcement: Mario Rodriguez (GitHub CPO), "GitHub Copilot is moving to
  usage-based billing," April 27, 2026.
  <https://github.blog/news-insights/company-news/github-copilot-is-moving-to-usage-based-billing/>
  Quote: "Today, we are announcing that all GitHub Copilot plans will transition to
  usage-based billing on June 1, 2026. Instead of counting premium requests, every
  Copilot plan will include a monthly allotment of GitHub AI Credits... Usage will be
  calculated based on token consumption, including input, output, and cached tokens,
  using the listed API rates for each model."
  Quote: "Starting June 1, premium request units (PRUs) will be replaced by GitHub AI
  Credits."
- Docs cross-reference confirming the same date after the fact: "Model multipliers for
  annual plans on request-based billing (legacy)" —
  <https://docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/model-multipliers-for-annual-plans>
  Quote: "On June 1, 2026, GitHub moved to usage-based billing. The model multipliers in
  this article apply only to Copilot Pro and Copilot Pro+ subscribers on an existing
  annual plan who remained on the legacy premium request-based billing model after
  June 1, 2026."
- The legacy premium-requests page itself is now framed as a retired/legacy reference:
  <https://docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/copilot-requests>
  Quote (page banner): "This article only applies to Copilot Pro and Copilot Pro+
  subscribers on an existing annual plan who remained on legacy premium request-based
  billing after June 1, 2026."

Mechanism confirmed: GitHub did **not** switch to "raw token billing" passed through
1:1. It introduced an intermediate unit called **GitHub AI Credits** (1 AI credit =
$0.01 USD), computed by multiplying token counts (input / output / cached) by published
per-model, per-1M-token rates, then converting the resulting USD amount to credits.

## 1. Billing model, unit, per-model price table, included allowances, budgets, overage

### 1.1 Unit and mechanism

- "GitHub AI Credits are the billing unit for metered Copilot usage... the interaction
  consumes tokens: input tokens (what's sent to the model), output tokens (what the
  model generates), and cached tokens (context the model reuses or stores). Each token
  is priced based on the model used, and the total is converted into AI credits, where
  1 AI credit = $0.01 USD."
  Source: "Usage-based billing for organizations and enterprises" —
  <https://docs.github.com/en/copilot/concepts/billing-and-usage/organizations-and-enterprises/billing>
  (same wording, individual-account framing, also in "Usage-based billing for
  individuals" —
  <https://docs.github.com/en/copilot/concepts/billing-and-usage/individuals/billing>)

### 1.2 Per-model price table (USD per 1,000,000 tokens)

Source for the whole table: "Models and pricing for GitHub Copilot" —
<https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing>
(retrieved 2026-10-29). Quote: "All prices are per 1 million tokens."

**OpenAI**

| Model | Tier | Threshold | Input | Cached input | Cache write | Output |
|---|---|---|---|---|---|---|
| GPT-5.3-Codex | Default | n/a | $1.75 | $0.175 | n/a | $14.00 |
| GPT-5.4 nano | Default | n/a | $0.20 | $0.02 | n/a | $1.25 |
| GPT-5.6 Luna | Default | ≤200K | $0.20 | $0.02 | $0.25 | $1.20 |
| GPT-5.6 Luna | Long context | >200K | $0.40 | $0.04 | $0.50 | $1.80 |
| GPT-5.6 Sol | Default | ≤272K | $4.00 | $0.40 | $5.00 | $20.00 |
| GPT-5.6 Sol | Long context | >272K | $8.00 | $0.80 | $10.00 | $30.00 |
| GPT-5.6 Terra | Default | ≤272K | $2.00 | $0.20 | $2.50 | $12.00 |
| GPT-5.6 Terra | Long context | >272K | $4.00 | $0.40 | $5.00 | $18.00 |
| GPT-6 Astra | Default | ≤272K | $10.00 | $1.00 | $12.50 | $50.00 |
| GPT-6 Astra | Long context | >272K | $20.00 | $2.00 | $25.00 | $75.00 |
| GPT-6 Luna | Default | ≤272K | $0.10 | $0.01 | $0.125 | $0.50 |
| GPT-6 Luna | Long context | >272K | $0.20 | $0.02 | $0.25 | $0.75 |
| GPT-6 Sol | Default | ≤272K | $2.00 | $0.20 | $2.50 | $10.00 |
| GPT-6 Sol | Long context | >272K | $4.00 | $0.40 | $5.00 | $15.00 |
| GPT-6.1 Sol | Default | ≤272K | $2.00 | $0.10 | $2.50 | $10.00 |
| GPT-6.1 Sol | Long context | >272K | $4.00 | $0.20 | $5.00 | $15.00 |
| GPT-6.1 Terra | Default | ≤272K | $1.00 | $0.05 | $1.25 | $5.00 |
| GPT-6.1 Terra | Long context | >272K | $2.00 | $0.10 | $2.50 | $7.50 |

Page note: "GPT-5.6 Sol, GPT-5.6 Terra, GPT-5.6 Luna, GPT-6 Astra, GPT-6 Luna, GPT-6
Sol, GPT-6.1 Sol, and GPT-6.1 Terra include a cache write cost in addition to cached
input. Earlier OpenAI models have no cache write cost."

**Anthropic** (all models include a cache-write surcharge per the page note: "Anthropic
models include a cache write cost in addition to cached input.")

| Model | Tier | Input | Cached input | Cache write | Output |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | Default | $1.00 | $0.10 | $1.25 | $5.00 |
| Claude Haiku 5.5 | Default (≤100K) | $0.10 | $0.01 | $0.125 | $0.50 |
| Claude Haiku 5.5 | Long context (>100K) | $0.50 | $0.05 | $0.625 | $2.50 |
| Claude Sonnet 4 | Default | $3.00 | $0.30 | $3.75 | $15.00 |
| Claude Sonnet 4.6 | Default | $3.00 | $0.30 | $3.75 | $15.00 |
| Claude Opus 4.8 | Default | $5.00 | $0.50 | $6.25 | $25.00 |
| Claude Opus 5 | Default | $5.00 | $0.50 | $6.25 | $25.00 |
| Claude Opus 5.5 | Default | $4.00 | $0.20 | $5.00 | $20.00 |
| Claude Sonnet 5 | Default | $2.00 | $0.20 | $2.50 | $10.00 |
| Claude Sonnet 5.5 | Default | $2.00 | $0.10 | $2.50 | $10.00 |
| Claude Opus 4.8 (fast mode, preview) | Default | $10.00 | $1.00 | $12.50 | $50.00 |
| Claude Fable 5 | Default | $10.00 | $1.00 | $12.50 | $50.00 |
| Claude Fable 5.1 | Default | $10.00 | $0.25 | $12.50 | $50.00 |

**Google** (no cache-write column shown, i.e. no cache-write surcharge documented)

| Model | Input | Cached input | Output |
|---|---|---|---|
| Gemini 3.8 Flash¹ | $0.75 | $0.075 | $3.75 |
| Gemini 4 Argon² | $2.00 | $0.10 | $10.00 |

Footnotes on the same page: "¹ Gemini 3.8 Flash is available at the promotional pricing
of $0.75 per 1M input tokens, $0.075 per 1M cached input tokens, and $3.75 per 1M output
tokens through December 31, 2026." / "² Gemini 4 Argon is available at the promotional
pricing of $2.00 per 1M input tokens, $0.10 per 1M cached input tokens, and $10.00 per
1M output tokens until December 1, 2026." (i.e. current Google prices in the table are
promotional/time-limited, not necessarily list price going forward.)

**Microsoft**

| Model | Input | Cached input | Output |
|---|---|---|---|
| MAI-Code-1.1-Flash | $0.20 | $0.02 | $1.20 |

**xAI**

| Model | Tier | Input | Cached input | Output |
|---|---|---|---|---|
| Grok 4.5 | Default (≤200K) | $2.00 | $0.50 | $6.00 |
| Grok 4.5 | Long context (>200K) | $4.00 | $1.00 | $12.00 |
| Grok 4.6 | Default (≤200K) | $2.00 | $0.50 | $6.00 |
| Grok 4.6 | Long context (>200K) | $4.00 | $1.00 | $12.00 |
| Grok 4.7 | Default (≤200K) | $2.00 | $0.50 | $6.00 |
| Grok 4.7 | Long context (>200K) | $4.00 | $1.00 | $12.00 |

**Moonshot AI**

| Model | Input | Cached input | Output |
|---|---|---|---|
| Kimi K3 | $3.00 | $0.30 | $15.00 |

**Image generation** (billed separately, text + image components)

| Model | Text input | Cached text input | Image input | Cached image input | Image output |
|---|---|---|---|---|---|
| GPT Image 2.5 Flare (preview) | $5.00 | $1.25 | $8.00 | $2.00 | $30.00 |

No table row exists in the fetched docs page for a "fine-tuned (GitHub)" custom model
(the section header "Fine-tuned (GitHub)" is present with an empty table) — flagged in
Gaps.

GPT-4.1/GPT-5-mini-class "mini" models and a distinct "Opus/Sonnet/Haiku"-labelled
Anthropic "mini" tier were **not found** as such; Anthropic's lightweight tier is Claude
Haiku (4.5/5.5) and OpenAI's lightweight tier is "Luna"/"nano" naming, not "mini" — see
Gaps for naming-convention caveat versus the user's implied Haiku/Sonnet/Opus and
mini/full/codex framing.

### 1.3 Included allowances per plan, budgets, hard limits, overage

**Individual plans** — "Usage-based billing for individuals":
<https://docs.github.com/en/copilot/concepts/billing-and-usage/individuals/billing>

| Plan | Price/month | Base credits | Flex allotment | Total monthly AI credits |
|---|---|---|---|---|
| Copilot Pro | $10 USD | 1,000 | 500 | 1,500 |
| Copilot Pro+ | $39 USD | 3,900 | 3,100 | 7,000 |
| Copilot Max | $100 USD | 10,000 | 10,000 | 20,000 |

Quote: "Base credits: These are included with your plan subscription each month... Flex
allotment: This is an additional monthly amount on top of your base credits... designed
to adapt as the economics of AI evolve." Base credits are consumed first, then flex.
Credits do not carry over; reset is "00:00:00 UTC on the first day of each calendar
month," independent of the user's billing date.

Copilot Free / Copilot Student: "have an allowance of AI credits and access to models
through auto model selection only. Copilot Free includes 2000 code completions per
month and Copilot Student includes unlimited code completions."

**Business / Enterprise (organizations)** — "Usage-based billing for organizations and
enterprises":
<https://docs.github.com/en/copilot/concepts/billing-and-usage/organizations-and-enterprises/billing>

| Plan | Total AI credits per user per month |
|---|---|
| Copilot Business | 1,900 |
| Copilot Enterprise | 3,900 |

Quote: "A user's included AI credits are pooled at the billing entity level. For
example, an enterprise with 100 Copilot Business users gets a shared pool of 190,000 AI
credits rather than 100 individual buckets." Unused credits do not carry over; reset at
00:00 UTC on the 1st of the month regardless of license add/remove timing.

Transitional promotional credits for existing Business/Enterprise customers (from the
April 27, 2026 blog post): "existing Copilot Business and Copilot Enterprise customers
will automatically receive promotional included usage for June, July, and August:
Copilot Business: $30 in monthly AI Credits; Copilot Enterprise: $70 in monthly AI
Credits."
<https://github.blog/news-insights/company-news/github-copilot-is-moving-to-usage-based-billing/>

**New "Copilot access" enterprise model** (rolling out from October 28, 2026) —
"What's changing with GitHub Enterprise and Copilot billing":
<https://docs.github.com/en/copilot/get-started/whats-changing-with-github-enterprise-and-copilot>

| Billing model | Per-user seat charge | Included AI credits |
|---|---|---|
| Copilot Business | $19 USD/month | 1,900/user/month, pooled |
| Copilot Enterprise | $39 USD/month | 3,900/user/month, pooled |
| Copilot access | $0 (with GitHub Enterprise Cloud license) or $10 USD/user/month (Copilot Standalone, no GHEC) | None — metered from first use |

Quote: "If you work with a GitHub or Microsoft account team: Available starting
October 28, 2026."

**Base plan prices unchanged** at the June 1, 2026 cutover, per the announcement blog:
"Copilot Pro remains $10/month, Pro+ remains $39/month, Business remains $19/user/month,
and Enterprise remains $39/user/month."

**Overage / hard limits / budgets** — "Budgets for usage-based billing":
<https://docs.github.com/en/copilot/concepts/billing-and-usage/organizations-and-enterprises/budgets>
and "Monitoring your GitHub AI Credits usage":
<https://docs.github.com/en/copilot/how-tos/manage-and-track-spending/monitor-ai-usage>

- Budget levels: user-level (universal, cost-center, individual — most-specific wins),
  cost-center, organization, enterprise. Quote: "The user-level budget (ULB) caps how
  many AI credits a single user can consume in a billing cycle... ULBs always enforce a
  hard stop. A $0 USD ULB immediately blocks features that consume AI credits."
- Overage behavior (org/enterprise), from
  <https://docs.github.com/en/copilot/concepts/billing-and-usage/organizations-and-enterprises/billing>:
  "Additional usage allowed: Usage continues at published per-credit rates... Note that
  additional usage may be capped: if you hit the cap, you'll need to pay off any
  additional usage you've already consumed in order to continue. Additional usage not
  allowed: Usage is blocked until the next billing cycle."
- No more "fallback to a cheaper model" behavior as under legacy premium requests. From
  the April 27, 2026 announcement: "Fallback experiences will no longer be available.
  Today, users who exhaust PRUs may fall back to a lower-cost model and continue
  working. Under the new model, usage will instead be governed by available credits and
  admin budget controls."
- Code completions / Next Edit Suggestions remain unlimited and are **not** billed in AI
  credits on any paid plan (both individual and org/enterprise billing pages state this
  verbatim).

## 2. Prompt caching

### 2.1 Cached input tokens — discounted, documented in the price tables above

Every per-model pricing row above has a distinct, lower "Cached input" price than
"Input" (typically 10x cheaper for OpenAI models, confirmed independently): "For most
OpenAI models that support cached input pricing, uncached input tokens cost 10 times as
much as cached input tokens." — "Getting more from each token" (VS Code blog), June 17,
2026 (updated June 18, 2026):
<https://code.visualstudio.com/blogs/2026/06/17/improving-token-efficiency-in-github-copilot>
(also linked from github.blog, same date, by Joe Binder:
<https://github.blog/ai-and-ml/github-copilot/getting-more-from-each-token-how-copilot-improves-context-handling-and-model-routing/>)

### 2.2 Cache write surcharge

- Confirmed billed, and explicitly priced per-model, for **Anthropic** models (all rows
  have a non-empty "Cache write" column) and for the newer **OpenAI** reasoning/agentic
  models (GPT-5.6 Luna/Sol/Terra, GPT-6 Astra/Luna/Sol, GPT-6.1 Sol/Terra). Quote:
  "Anthropic models include a cache write cost in addition to cached input." / "GPT-5.6
  Sol, GPT-5.6 Terra, GPT-5.6 Luna, GPT-6 Astra, GPT-6 Luna, GPT-6 Sol, GPT-6.1 Sol, and
  GPT-6.1 Terra include a cache write cost in addition to cached input. Earlier OpenAI
  models have no cache write cost."
  Source: <https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing>
- Google, xAI, Moonshot AI, and Microsoft rows in the same table have **no** cache-write
  column at all, implying no separate cache-write charge is billed for those providers
  (UNVERIFIED as an explicit negative statement — the docs page simply omits the
  column for those vendors rather than stating "no cache write cost").

### 2.3 Cache TTL (5 min / 1 h) — exposed/controllable?

**Confirmed for OpenAI models in GitHub Copilot for VS Code only**, via a GitHub-managed
backend setting, not a user-facing toggle. Source: "Getting more from each token" / VS
Code technical deep-dive (same June 17-18, 2026 post):
<https://code.visualstudio.com/blogs/2026/06/17/improving-token-efficiency-in-github-copilot>
Quote: "Caching the prefix happens on its own, but how long that cache survives is
something we can configure. After careful evaluation, we enabled extended prompt
caching for supported models through the `prompt_cache_retention` body parameter. By
default, the cache lives in fast GPU memory, where it is dropped after about 5 to 10
minutes of inactivity (up to an hour in some cases) to make room for other work.
Setting `"prompt_cache_retention": "24h"` moves the cache to slower but roomier
GPU-local storage and keeps it for up to 24 hours."

This matches the user's "5 min / 1 h" framing almost exactly (default TTL "5 to 10
minutes... up to an hour in some cases"), plus reveals GitHub has opted supported OpenAI
models into a 24-hour extended-retention tier, configured by GitHub's harness (the VS
Code Copilot extension), not by the end user. Cache hit-rate improvements measured:
"+13%" to "+919%" relative increase across GPT-5.2 / GPT-5.3-Codex / GPT-5.4 depending
on the gap between requests (10–60 min buckets), per the same post.

For **Anthropic** models, the mechanism is different and user/harness-controlled via
explicit breakpoints, not a provider-inferred TTL knob: "Anthropic's prompt caching
works differently from the automatic prefix caching that OpenAI models use. Rather than
the provider inferring the reusable prefix, the caller places explicit `cache_control`
breakpoints, and the API caches everything up to each marker... [VS Code] uses the
Messages API caching to spend up to four breakpoints deliberately... A pair of rolling
anchors on the two most recent cacheable messages." Same source as above. No explicit
TTL value (e.g. Anthropic's public 5-min/1-hour cache_control TTL options) is stated in
this GitHub-authored post — UNVERIFIED whether Copilot exposes Anthropic's 1-hour TTL
option specifically.

No evidence found that **Copilot CLI** (as opposed to VS Code) exposes any
cache-retention or TTL configuration option; the CLI reference's `/usage` command and
environment-variable list contain no `prompt_cache_retention`-equivalent control. Source
reviewed: "GitHub Copilot CLI command reference":
<https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference>
(full-text grep for "cache"/"ttl" — only unrelated MCP tool-snapshot caching and
OTel GenAI cache-token attributes were found, not a retention/TTL setting). Flagged in
Gaps.

### 2.4 Does Copilot pass through Anthropic/OpenAI prompt caching?

Confirmed yes, functionally: Copilot's backend forwards requests so that Anthropic's
`cache_control` breakpoints and OpenAI's automatic prefix caching (plus the
`prompt_cache_retention` parameter) are actually used against the upstream provider
APIs, and the resulting cached-token counts and savings are passed through to Copilot's
own per-model "Cached input" billing rate. Source: same VS Code blog post above,
corroborated by the OTel GenAI attributes in the CLI reference, which separately report
`gen_ai.usage.cache_read.input_tokens` and `gen_ai.usage.cache_creation.input_tokens` —
i.e., Copilot surfaces the raw provider cache-read/cache-creation token counts, which is
only possible if the underlying provider caching mechanism is being used. Source:
<https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference>
(OpenTelemetry monitoring section, GenAI Semantic Conventions attribute table).

## 3. Subagents / background agents / coding agent — same billing? Auto-selection discount?

### 3.1 Billed identically, same per-token rates

- Copilot CLI subagent calls are billed as ordinary model calls: the SDK docs state
  "The `assistant.usage` event is emitted once for every model API call in a turn
  (including calls made by sub-agents)." Source: "Usage and billing metrics" (Copilot
  SDK docs): <https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/usage-and-billing>
- Copilot cloud agent (the former "coding agent") consumes AI credits the same way as
  interactive chat: "Copilot cloud agent uses one premium request per session,
  multiplied by the model's rate" (legacy framing, pre-June 2026) — and post-transition,
  it is explicitly listed alongside Chat/CLI/Spaces as a feature that "consumes AI
  credits": "Copilot Chat / Copilot CLI / Copilot cloud agent / Copilot Spaces / Spark /
  Third-party coding agents" all appear in the "What is billed in AI credits?" list on
  both the individual and org/enterprise billing pages (sources above, section 1.3).
  Reasoning-effort choice directly affects cost: "Higher reasoning levels can improve
  the quality of responses to complex tasks, but may take longer and use more AI
  credits." Source: "Changing the AI model" (cloud agent docs):
  <https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/changing-the-ai-model>
- Pre-June-2026 legacy note found while researching: "Premium requests for Spark and
  Copilot cloud agent are tracked in dedicated SKUs from November 1, 2025." Source:
  legacy requests page:
  <https://docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/copilot-requests>
  (historical/legacy fact, included for completeness, not current post-June-2026
  behavior).

### 3.2 Auto model selection discount

Confirmed **10%** discount, applies to Copilot Chat and Copilot cloud agent (not
explicitly stated for Copilot CLI post-transition — see caveat below). Source: "About
GitHub Copilot auto model selection":
<https://docs.github.com/en/copilot/concepts/models/auto-model-selection>
Quote: "If you are on a paid Copilot plan, you qualify for a 10% discount on model costs
while using auto model selection in Copilot Chat, or Copilot cloud agent."
Same figure repeated in "Usage-based billing for individuals": "If you are on a paid
Copilot plan, you qualify for a 10% discount on model costs while using auto model
selection in Copilot Chat, or Copilot cloud agent."
<https://docs.github.com/en/copilot/concepts/billing-and-usage/individuals/billing>

Caveat: the legacy model-multipliers page states the 10% discount historically also
applied to "Copilot CLI" and "the GitHub Copilot app": "If you use auto model selection
in Copilot Chat, Copilot CLI, the GitHub Copilot app, or Copilot cloud agent, you
qualify for a 10% discount." Source:
<https://docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/model-multipliers-for-annual-plans>
— but that is a legacy (pre-June-2026 annual-plan) page; the current post-transition
pages only name Chat and cloud agent. Whether Copilot CLI still receives the 10% auto
discount post-June-2026 is UNVERIFIED from current docs (flagged in Gaps).

### 3.3 Copilot Fusion (router) discount — distinct mechanism from "auto"

Confirmed a separate, larger, **time-limited 30% discount**: "About GitHub Copilot
Fusion": <https://docs.github.com/en/copilot/concepts/models/copilot-fusion>
Quote: "Through November 30, 2026, users on paid Copilot plans receive a 30% discount on
model costs when using Copilot Fusion." Also: "When you use Copilot Fusion, you're
billed for each model it uses, at that model's standard rate. There's no separate
charge for Copilot Fusion. Because Fusion High and Fusion Max can use more than one
model for a task, a task may consume more AI credits than it would with Fusion
Standard."

## 4. Cost visibility: how to see token usage/cost per session/request

### 4.1 Copilot CLI `/usage`

Confirmed. Source: "GitHub Copilot CLI command reference":
<https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference>
Quote (table row for `/usage`): "Display session usage metrics and statistics,
including per-model token totals. For token-based-billing accounts, each model's row
also shows its own AI credit consumption (for example, 1 AIC). Billed models with no
token counts show credits only."

### 4.2 Account/org usage dashboards and reports

- Individual: billing overview → "AI usage" page at
  `https://github.com/settings/billing`, side bar "AI usage": "How many included
  credits you have used... How much additional usage you've consumed beyond your plan's
  included amount... A chart showing which models you've used... A breakdown of the
  models used, the credits consumed per model, and the cost." Source: "Monitoring your
  GitHub AI Credits usage":
  <https://docs.github.com/en/copilot/how-tos/manage-and-track-spending/monitor-ai-usage>
  Quote (limitation): "The AI usage page shows credits consumed and costs by model.
  However, you generally cannot trace consumed credits to specific prompts, sessions,
  or exact features at a per-request level." — i.e. GitHub's own web UI does **not**
  give per-request cost traceability; that granularity is only available via the SDK
  events/OTel (section 4.3/4.4) or Copilot CLI `/usage`.
- Business/Enterprise: per-user consumption visible under "Copilot settings" → "Usage
  this cycle" card (same source).
- IDE status-bar indicators for VS Code, Visual Studio, JetBrains, Xcode, Eclipse (same
  source, "Viewing usage in your IDE" section).
- Downloadable usage report referenced ("Viewing your usage of metered products and
  licenses") — link target not independently fetched in this research pass (Gaps).
- Blog-confirmed API/UI rollout dates for this reporting capability:
  - "Copilot users can now see AI credits used per billing cycle" — July 20, 2026,
    github.blog Changelog (found via blog search; full article URL not independently
    opened in this pass, cite via search result):
    <https://github.blog/?s=AI+credits+copilot> (search results page, retrieved
    2026-10-29) — UNVERIFIED at full-article level, flagged in Gaps.
  - "AI credits consumed per user now in the Copilot usage metrics API" — June 19, 2026,
    github.blog Changelog. Quote from search snippet: "The Copilot usage metrics API now
    reports how many AI credits each user consumed per day, derived from the same AI
    credits consumption data used in the usage-based billing API." Same caveat: found via
    blog search listing, full article not independently opened — UNVERIFIED at
    full-article level, flagged in Gaps.

### 4.3 Copilot SDK (programmatic, per-call and per-session)

Source: "Usage and billing metrics" (Copilot SDK docs):
<https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/usage-and-billing>

| Signal | API | Scope | Type |
|---|---|---|---|
| Per-call token counts | `assistant.usage` event | Session | Event |
| Context-window utilization | `session.usage_info` event | Session | Event |
| Context-window breakdown (on demand) | `session.metadata.contextInfo` | Session | RPC |
| Accumulated AI credit and token totals | `session.usage.getMetrics` | Session | RPC |
| Per-model AI credit pricing | `models.list` | Server | RPC |
| Account quota and premium interactions | `account.getQuota` | Server | RPC |

Quote: "The `assistant.usage` event is emitted once for every model API call in a turn
(including calls made by sub-agents). It carries the token counts and the billing
multiplier for that single call." Fields: `model`, `inputTokens`, `outputTokens`,
`cost` (described as "Premium request multiplier applied to this call" — note the field
name/description still uses legacy "premium request multiplier" terminology even though
the surrounding docs describe token-based AI-credit billing; flagged in Gaps as a
possible terminology inconsistency in the docs).

### 4.4 OpenTelemetry export (Copilot CLI)

Confirmed, detailed. Source: "GitHub Copilot CLI command reference," "OpenTelemetry
monitoring" section:
<https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference>

Quote: "Copilot CLI can export traces and metrics via OpenTelemetry (OTel), giving you
visibility into agent interactions, LLM calls, tool executions, and token usage. All
signal names and attributes follow the OTel GenAI Semantic Conventions. OTel is off by
default with zero overhead. It activates when any of the following conditions are met:
`COPILOT_OTEL_ENABLED=true`; `OTEL_EXPORTER_OTLP_ENDPOINT` is set;
`COPILOT_OTEL_FILE_EXPORTER_PATH` is set."

Key environment variables documented: `COPILOT_OTEL_ENABLED`,
`OTEL_EXPORTER_OTLP_ENDPOINT`, `COPILOT_OTEL_EXPORTER_TYPE` (`otlp-http` or `file`),
`OTEL_EXPORTER_OTLP_PROTOCOL`, `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`,
`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`, `OTEL_LOG_LEVEL`,
`COPILOT_OTEL_FILE_EXPORTER_PATH` ("Write all signals to this file as JSON-lines"),
`COPILOT_OTEL_SOURCE_NAME`, `OTEL_EXPORTER_OTLP_HEADERS`.

GenAI span/metric attributes documented include `gen_ai.usage.cache_read.input_tokens`
and `gen_ai.usage.cache_creation.input_tokens` (both "Both" scope — i.e. present on both
traces and metrics), confirming cache-token accounting is exported via OTel, in addition
to standard input/output token counts. The runtime emits a span tree per agent
interaction: "an `invoke_agent` root span, with `chat` and `execute_tool` child spans,"
and explicitly notes "Both top-level sessions and subagent invocations (for example,
explore, task) use span kind `INTERNAL`... provider-facing inference is represented by
child `CLIENT` chat spans" — i.e. subagent token usage is separately traceable via OTel.
Can also be configured via VS Code settings or an enterprise `managed-settings.json`
(same source, links to "Enable OTel monitoring in the VS Code documentation" and
"Enterprise managed settings" — those two linked targets were not independently opened
in this pass; flagged in Gaps).

### 4.5 Local log files

Confirmed. Default log directory: `~/.copilot/logs/` (overridable via `--log-dir`
flag). Source: same CLI command reference as above.
Quote: "`--log-dir=DIRECTORY` Set the log file directory (default:
`~/.copilot/logs/`)." Debug-log collection command: `/collect-debug-logs
[file|gist|share] [PATH]` — "Collect debug logs to an archive, a GitHub gist, or [for]
sharing debug logs." User settings file: `~/.copilot/settings.json`;
MCP config: `~/.copilot/mcp-config.json`.

File **format** of the OTel file exporter is JSON-lines (per
`COPILOT_OTEL_FILE_EXPORTER_PATH` description above): "Write all signals to this file as
JSON-lines." The format of the plain debug logs in `~/.copilot/logs/` is not specified
in the fetched docs (UNVERIFIED — plain text vs. structured JSON not stated).

## 5. Model multipliers — what's left of "premium requests"

Confirmed: the premium-request/model-multiplier system is **retired** for all
usage-based-billing accounts and survives only as a **legacy carve-out** for a narrow
population. Source: "Requests in GitHub Copilot (legacy)":
<https://docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/copilot-requests>
Quote: "This article only applies to Copilot Pro and Copilot Pro+ subscribers on an
existing annual plan who remained on legacy premium request-based billing after June 1,
2026."

Who is still on it, and how they got there: from the April 27, 2026 announcement —
"Users on a monthly Pro or Pro+ plan will automatically migrate to usage-based billing
on June 1, 2026. Users on annual Pro or Pro+ plans will remain on their existing plan
with premium request-based pricing until their plan expires. Model multipliers will
increase on June 1 (see table) for annual plan subscribers only. At expiration, they
will transition to Copilot Free with the option to upgrade to a paid monthly plan."
<https://github.blog/news-insights/company-news/github-copilot-is-moving-to-usage-based-billing/>

Legacy multiplier table still published (for that shrinking annual-plan population),
source: "Model multipliers for annual plans on request-based billing (legacy)":
<https://docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/model-multipliers-for-annual-plans>

| Model | Multiplier |
|---|---|
| Claude Haiku 4.5 | 0.33 |
| Claude Opus 4.8 | 27 |
| Claude Sonnet 4.6 | 9 |
| Gemini 3 Pro | 6 |
| GPT-4o | 0.33 |
| GPT-4o mini | 0.33 |
| GPT-5.1 | 3 |
| GPT-5.1-Codex | 3 |
| GPT-5.1-Codex-Mini | 0.33 |
| GPT-5.1-Codex-Max | 3 |
| GPT-5.3-Codex | 6 |
| MAI-Code-1.1-Flash | 0.25 |

Quote: "Model multipliers are a concept specific to the legacy premium request-based
billing system, and do not apply to GitHub's new usage-based billing model." Also:
"Copilot code review has a model multiplier of 13" under the legacy system (and
"Starting June 1, 2026, Copilot code review will have a model multiplier of 13" per the
pre-cutover legacy requests page) — this multiplier concept has no equivalent numeric
"multiplier" in the usage-based system; instead, code review cost is expressed directly
in AI-credit/USD ranges per "effort level" (Lite/Balanced/Max), e.g. "Balanced: $0.25 USD
to $5 USD, approximate average $1.50 USD" per review. Source: "Models and pricing for
GitHub Copilot," "Pricing and usage cost considerations for Copilot code review" section:
<https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing>

The SDK's `assistant.usage` event still names its per-call cost field `cost` and
describes it as "Premium request multiplier applied to this call" even under
token-based accounts — residual terminology, not a surviving billing mechanism (see
Gaps). Source:
<https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/usage-and-billing>

Legacy premium-request allowances, retained here for reference only (apply solely to
the annual-plan holdouts described above):

| Plan | Price | Premium requests/month | Extra requests |
|---|---|---|---|
| Copilot Pro | $10 USD/month | 300 | $0.04/request |
| Copilot Pro+ | $39 USD/month | 1,500 | $0.04/request |

Source: <https://docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/copilot-requests>
Quote: "Billing for premium requests began on June 18, 2025, for all paid Copilot plans
on GitHub.com, and on August 1, 2025, on GHE.com."

## Gaps

The following could not be fully verified in this research pass, or were only partially
corroborated, within the primary sources accessed on 2026-10-29:

1. **Full-article confirmation of two changelog posts** found only via github.blog's
   on-site search-results snippets, not opened as full articles: "Copilot users can now
   see AI credits used per billing cycle" (dated July 20, 2026 per search snippet) and
   "AI credits consumed per user now in the Copilot usage metrics API" (dated June 19,
   2026 per search snippet). The underlying full-article URLs were not resolved/fetched
   directly; only the search-listing text is cited above.
2. **Copilot CLI's current eligibility for the 10% auto-model-selection discount**
   post-June-2026: the legacy model-multipliers page names "Copilot Chat, Copilot CLI,
   the GitHub Copilot app, or Copilot cloud agent" as eligible for the 10% discount, but
   the current (post-transition) "About GitHub Copilot auto model selection" and
   "Usage-based billing for individuals" pages name only "Copilot Chat, or Copilot cloud
   agent." Whether Copilot CLI retains the 10% discount under usage-based billing is not
   explicitly stated either way in the current docs.
3. **Anthropic 1-hour cache_control TTL option**: GitHub's own blog post describes
   Anthropic prompt caching via "explicit `cache_control` breakpoints" and "rolling
   anchors," but does not state whether Copilot's backend uses/exposes Anthropic's
   documented 5-minute vs. 1-hour TTL choice specifically (as opposed to OpenAI's
   `prompt_cache_retention` parameter, which is explicitly documented).
4. **Copilot CLI cache-retention/TTL control**: no environment variable, flag, or
   `/settings` option equivalent to VS Code's backend `prompt_cache_retention` behavior
   was found in the CLI command reference. It is unclear whether the CLI benefits from
   the same extended-retention backend change described for VS Code, or whether that
   improvement is VS-Code-extension-specific.
5. **Negative confirmation of "no cache write cost" for Google, xAI, Moonshot AI, and
   Microsoft models**: the pricing table simply omits a "Cache write" column for these
   vendors' rows; the docs do not explicitly state "no cache write charge applies" the
   way they do for OpenAI's older models ("Earlier OpenAI models have no cache write
   cost"). Treated as implied-by-omission, not an explicit claim.
6. **"Fine-tuned (GitHub)" custom-model pricing row**: the pricing page includes a
   "Fine-tuned (GitHub)" category header with an empty table (no model rows found at
   fetch time), so no pricing data exists for this category as of 2026-10-29.
7. **Downloadable usage report mechanics and format** ("Viewing your usage of metered
   products and licenses," linked from the AI-usage monitoring doc) and the two
   OTel-linked pages ("Enable OTel monitoring in the VS Code documentation," "Enterprise
   managed settings") were referenced but not independently opened/verified in this
   research pass.
8. **Plain-text debug log format** in `~/.copilot/logs/` (as opposed to the explicitly
   JSON-lines `COPILOT_OTEL_FILE_EXPORTER_PATH` output) is not documented — its exact
   format/schema is unknown from primary sources reviewed.
9. **Official github.com/pricing and docs.github.com/en/billing REST API endpoint
   specifics** for budgets/usage (e.g., GitHub REST API routes for creating/reading
   budgets, referenced generically as "the REST API... see Budgets") were not
   individually enumerated with exact endpoint paths in this pass.
10. User's framing of model families as "Haiku/Sonnet/Opus," "mini/full/codex," and a
    generic "Gemini" catch-all does not map 1:1 onto GitHub's actual current catalog
    naming (e.g., OpenAI's lightweight/versatile/powerful tiers are named
    Luna/Terra/Sol/Astra/nano, not "mini"; no model literally named "GPT mini" appears
    in the live pricing table, only in the retired legacy multiplier table as "GPT-4o
    mini"). This is a terminology/catalog-evolution gap rather than a missing data
    point.
