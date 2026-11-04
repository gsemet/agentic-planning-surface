# Requirements: cost-controlled change-request factory on Copilot CLI

## R0. Absolute priority

Token cost control. Since June 2026, billing is token-based in AI Credits and the budget is
tight. Every design choice must state its token cost.

## R1. Roles

| Role | Nature | Lifetime |
|------|--------|----------|
| Chief of Staff | Main interactive session. The user grills, steers and changes direction here | Whole programme |
| Foreman | Translates instructions, schedules lots, optimises quality per credit | Ends when all lots are done |
| Driver | Hired per Change Request, isolated (usually its own worktree) | One CR |
| Coder | Subagent of a Driver; implements | One attempt |
| Inspector | Subagent of a Driver; hyper-critical review of the same task | One review |
| Stack manager | Optional sub-session for stacked PRs (`gh stack`) or MRs (`glab stack`) | As needed |

The Driver decides whether an Inspector critique is worth another Coder round.

## R2. Live intervention during implementation (hard requirement)

The user regularly intervenes **while lots are in flight**:

1. Review a task in progress to influence it.
2. Fix an open PR, so the Foreman must tell the affected Driver about a last-minute change.
3. Add a task.
4. Reorder tasks.

Consequence: a fixed, journaled pipeline is not enough.
Copilot **dynamic workflows** were tried and rejected for this reason:

- Their subagents cannot receive messages (`read_agent` and `write_agent` cannot see them).
- The plan is code, fixed at launch. Adding or reordering lots means cancelling and resuming.

Every running Driver must therefore be **addressable** and must take in new instructions at
predictable points, at no token cost while it waits.

### R2.1 Decisions (user, 2026-10-29)

- Interventions always go **Chief of Staff → Foreman → Driver** as a message.
  The user never talks to a Driver directly.
- The **Driver decides** how to apply a message: interrupt the running Coder now, or let it
  finish and request the change in the next round.
  The Driver must therefore be able to receive a message while its Coder subagent runs.

### R2.2 Decisions (user, grill round 1)

- Runtime: **VS Code Agents host** (`create_session`, `send_message`), not the bare CLI terminal.
- Foreman: a **nested LLM session** created by the Chief of Staff, model **Claude Opus 5.5,
  low reasoning effort**, with the smallest possible context.
- Drivers: **sibling sessions** created by the Foreman, so its turn ends and it stays
  reachable.
- Foreman wake-up: (1) each Driver messages the Foreman when it finishes or is blocked, and
  (2) a periodic `/every` watchdog catches stuck states.

### R2.3 Decisions (user, grill round 2)

- Foreman context: impose a **custom Foreman agent with a minimal tool allowlist now**.
  Whether `create_session` can start a session on a custom agent is untested (no such
  parameter); see test T1.2b.
- Foreman memory: **one long-lived Foreman** for the whole batch, with automatic compaction if
  needed. Accepts the cache rebuild cost of compaction.
- Watchdog: **`/every 4m` inside the Opus Foreman**, under the 5 min Claude TTL, so the cache
  stays warm. Estimated $0.15/h idle; to be measured. `/every` in the VS Code host is untested.

### R2.4 Decisions (user, grill round 3)

- Driver model: **`gpt-6.1-sol`** (30 min cache TTL).
- Escalation: the **Driver escalates the Coder model on its own and notifies the Foreman**.
- At most **2 Coder → Inspector rounds**; then the Driver escalates or reports.
- The **Driver pushes its branch and opens the PR or MR** itself.

### R2.5 Forge rules for every agent that touches GitHub or GitLab

Drivers may work on GitLab (`glab`) or GitHub (`gh`). Agents must never hit a pager, an editor
or an interactive menu, because a blocked command burns time and credits.

| Tool | Rule |
|------|------|
| `glab` | Prefix every call with `GLAB_PAGER=cat` (`PAGER`/`GIT_PAGER` do not control glab) |
| `glab ci status --live` | Also set `GLAB_NO_PROMPT=true` |
| `glab ci view`, `glab ci trace` | Forbidden; use `glab ci get --output json` and `glab api .../jobs/<id>/trace` |
| `glab mr create` | Always `--push`; pass `--description` explicitly, never `-` |
| `glab ... note` | Always `-m` or stdin; never open `$EDITOR` |
| Self-hosted GitLab | `--repo <host>/group/project` (e.g. `gitlabee.xxx.com`)        |
| `gh` | Set `GH_PAGER=cat` and `GH_PROMPT_DISABLED=1`; pass `--body` or `--body-file` explicitly |
| `git` | `git --no-pager`; `GIT_EDITOR=true` for rebase and merge |
| Both | Prefer JSON output (`--output json`, `--json`) for anything an agent parses |

These rules go into the Driver and Stack manager agent files, not into a shared instruction file,
to keep other prefixes small.

### R2.6 Decisions (user, grill round 4)

- Budget: the **Foreman** meters every Driver with
  [copilot-session-usage](https://github.com/gsemet/copilot-session-usage):
  `UV_NO_CONFIG=1 uv tool run copilot-session-usage --agent cli analyze
  ~/.copilot/session-state/<id> --query <field>`. VS Code host sessions are stored there too.
- Coder and Inspector: **`gpt-5.6-luna`, reasoning effort max**.
- State: **one JSON file**, written only by a script (`factory.py`, PEP 723) that locks the
  file and writes atomically (temp file plus rename). LLMs never edit it directly; they call
  `factory.py <command>`. The Chief of Staff reads it with `factory.py status`.
- Every Python script, for every role, runs with **`uv run`** (PEP 723 inline metadata), never
  `python` or `python3`: `uv run factory.py status`, `uv run session_cost.py <events.jsonl>`.
  This rule goes into every agent file.

## R3. Measured constraints

See [evidence/local-telemetry-findings.md](./evidence/local-telemetry-findings.md).

- A message to a busy LLM turn can wait minutes. A kill signal sent through an LLM arrived after
  the work had finished.
- No completion notification reaches a parent chat; state must be read, not awaited.
- Orchestration on a frontier model cost 99 % of the simulation run.
- Claude cache TTL is 300 s and GPT cache TTL is 1800 s. Cache writes cost 125 % of input.
