# Comparison report: session factory vs dynamic workflow

Date: 2026-10-29. Host: VS Code Agents host, Copilot CLI 1.0.105, token-based billing.
Evidence: [tests/](./tests/README.md), series 02–07. Costs come from
`evidence/scripts/session_cost.py` applied to each session's `events.jsonl` (the same method for
every series). The Chief of Staff's own cost is excluded everywhere.

## 1. Summary

- The cheapest working solution is the **dynamic workflow** (series 07): **$0.028 for 5 CRs**,
  one mid-run change and one defect caught and fixed. The best session-based run (06b) cost
  **$0.62** for the same scenario: **22× more**.
- The gap is a **fixed orchestration overhead** of about **$0.12 per CR**: the Foreman and Driver
  main sessions each re-send a prefix of about 30k tokens on every call. A workflow has no main
  session; its orchestration is code and costs nothing.
- The state tooling (`factory.py` CLI vs a markdown board) does **not** change the bill:
  Foreman $0.18 (04b, CLI) vs $0.20 (06b, `BOARD.md`).
- **The model is the main lever inside the session design**: Sol instead of Opus cut the
  Foreman cost by 69 % (04a vs 04b).
- **`/every` must never run on a session that steers others**: it made host tools hang (03 and 06).
- Recommendation: a **hybrid**. A dynamic workflow serves as the Foreman engine. The Chief of Staff
  chat steers it through an inbox file. LLM judges and session-based Drivers come in only by
  escalation.

## 2. Solutions compared

| | A. Opus Foreman + state CLI | B. Sol Foreman + state CLI | C. Sol Foreman, nested, no tooling | D. Dynamic workflow |
|---|---|---|---|---|
| Series | 02, 04a | 04b | 06b | 07 |
| Foreman | Opus 5.5 session | Sol session | Sol independent session | workflow code |
| Drivers | Sol sessions | Sol sessions | Sol chats nested in the Foreman | code (rule) |
| Coder / Inspector | Luna custom agents | Luna custom agents | Luna custom agents | Luna custom agents |
| State | `factory.py` + JSON | `factory.py` + JSON | `BOARD.md` | `inbox.json` + run journal |
| Steering channel | `send_message` | `send_message` | `send_message` | edit `inbox.json` |

## 3. Cost

| Solution | CRs | Total USD | Per CR | Orchestration share | Coder + Inspector |
|----------|----:|----------:|-------:|--------------------:|------------------:|
| A (04a) | 5 + 1 order | 1.06 | 0.21 | about 97 % | about 3 % |
| B (04b) | 5 + 1 order | 0.68 | 0.14 | about 96 % | about 4 % |
| C (06b) | 5 + 1 change | 0.62 | 0.12 | **96 %** (Foreman 0.20, Drivers 0.40) | 0.024 |
| D (07) | 5 + 1 change + 1 fix | **0.028** | **0.006** | **0 %** | 0.028 |

Where the tokens go in C: each Sol main session carries the system prompt, the tool definitions
and the conversation, about 30k tokens, re-read from cache on each of its 7–14 calls. The
actual work (Luna Coder and Inspector, whose custom-agent prefix is about 2.7k) is 4 % of the bill.

**Caveat:** the CRs are toy-sized. On real CRs the Coder and Inspector cost grows, so the 22×
ratio shrinks. The absolute saving of about $0.12 per CR in orchestration stays.

## 4. Capabilities against the user's needs

| Need | C. Session factory | D. Dynamic workflow |
|------|--------------------|---------------------|
| Add a task mid-run | yes (`[CoS] add`) | yes (append to `inbox.json`) |
| Change a running task | yes; the Driver chooses steer, restart or defer, and can steer a running Coder with `write_agent` | yes, at the next step boundary; a running Coder cannot be steered |
| Reorder | yes (Foreman) | yes (order or priority in the inbox; not in the kit yet) |
| Review a task in progress | open the Driver chat and ask it | read its worktree and the run log; no one to talk to |
| Fix an already delivered CR (open PR) | yes (Driver reopens) | needs a reopen rule (not in the kit yet) |
| Judgement "is this finding worth a round?" | LLM (Driver) | rule; an LLM judge only when needed |
| Visible hierarchy in the UI | yes (nested chats) | no (one run with progress lines) |
| Clean end of life | CoS deletes the Foreman session, which removes the Drivers | the run returns; nothing remains |
| Hard budget ceiling | none | `limits.maxAiCredits` per run |
| Robustness | `/every` causes hangs; FINAL can race with a late Driver report | experimental API; headless mode needs pre-granted permissions |

## 5. With or without tooling

- **State CLI vs markdown board:** no measurable token difference (Foreman 0.18 vs 0.20).
  The board is simpler and readable by a human. The CLI only helps if it computes something the
  LLM would otherwise reason about, such as dependency readiness or stale Drivers.
- **Code as tooling (the workflow)** is a different kind of thing: it removes the LLM from scheduling and
  routine judgement. That is where the cost disappears.
- Rule of thumb: **every decision that a rule can take must be code**. Keep the LLM for writing
  code, criticising it, and the rare ambiguous judgement.

## 6. Recommendations

1. **Foreman engine = dynamic workflow.** It is a pull-based worker pool over an inbox, with
   one worktree per CR and a Coder → Inspector → rule loop. Set `maxAiCredits` per run and
   `maxConcurrentSubagents` for parallelism.
2. **Chief of Staff = the only conversation.** It turns the user's directions into inbox entries:
   `add`, `change`, `reorder`, `reopen`, `cancel`, `close`. It reads progress from the run log and
   the worktrees. Its own cost is the user's conversation, and nothing else polls.
3. **Escalation ladder, in code:**
   1. Round 1–2: Luna Coder, Luna Inspector, judged by rule.
   2. Inspector still blocking: one `ctx.agent` judge call (Sol) decides fix, accept or escalate.
   3. Escalate: rerun the Coder with `model: "gpt-6.1-sol"`.
   4. Still failing: hand the CR to an interactive Driver session that the CoS creates on
      demand, as an independent session in the CR worktree, for a human deep-dive.
4. **Never put `/every` on a session that uses host tools.** If a timer is needed, use a
   bash-only session that does nothing else, or a workflow-level `sleep`.
5. **Measure every run:** archive the run's `events.jsonl` and price it with
   `session_cost.py`. Record USD per CR, rounds, and escalations, and keep a history to tune
   the thresholds.
6. **Keep the session factory (C) as the fallback** for CRs that need a conversation. Run it with
   a Sol Foreman, no heartbeat, nested Drivers, and drain each Driver's queue before it reports.

## 7. Open risks

- Dynamic workflows are in public preview; the API and the billing may change.
- Headless runs need `--allow-all-tools` and `--add-dir`: run them in a dedicated lab or worktree,
  never in a directory that holds secrets.
- A running Coder cannot be steered inside a workflow. A change that arrives mid-Coder costs at
  most one wasted Coder call (about $0.003 on Luna).
- The hang caused by `/every` is a host bug that may be fixed later; re-test before relying on it.

## 8. Next test (series 08 proposal)

Hybrid on a real repository:
- The CoS chat drives the workflow through the inbox.
- Cover `reorder`, `reopen` of a delivered CR, a forced escalation to Sol, and a hand-off to an
  interactive Driver session.
- Use CRs large enough that the Coder cost dominates, to measure the real ratio.
