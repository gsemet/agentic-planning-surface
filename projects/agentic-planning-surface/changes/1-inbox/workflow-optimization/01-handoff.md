# Handoff: optimise the change-request factory (cost, measurement, Claude Code + Copilot)

Written 2026-10-27 by the main Claude Code session (Opus 5.5) at the user's request, to continue a
**design discussion** in a new session. Nothing has been built for this topic yet: the user asked
for options and questions only ("on est sur une phase de réflexion, ne fais rien").

**Talk with the user in French.** Everything written to repositories stays in English.

## 1. The goal (user's words, translated)

Improve the generic skill
[`.claude/skills/change-request-factory/`](../../../../../.claude/skills/change-request-factory/SKILL.md)
of `agentic-planning-surface`. It should be able to replace the Studio project's process guideline
[`change-requests-lifecycle.guidelines.md`](../../../../../../markdown-okf-schema-studio/.agents/guidelines/change-requests-lifecycle.guidelines.md).
**Do not migrate the Studio yet**: the aim is to improve the skill.

The user's goals:

- **Cut token cost as far as possible.**
- **Keep the same features.** The user talks to an intermediary (the main session). The
  intermediary drives orchestrators, each orchestrator drives its drivers, and each driver runs
  coder and reviewer rounds. Also kept: backlog, grill, parallel CRs, stacked PRs, CI watching,
  landing and demo tour.
- **Dynamic workflows may play a role.** The meaning is not yet clarified with the user (see §6).
- **Python CLIs may help.** They run with `uv run` and PEP 723 inline metadata, to cut tokens and
  automate tracking. Examples from the user:
  - generate the tracking Markdown from JSON;
  - lint those JSON files so agents see errors at once;
  - maybe provide interfaces.

  The user also said: "not over-engineered; let's think about what is possible together".
- **Design with very precise measurements** ("un design avec des mesures hyper précises").
- **The design must work for both Claude Code and GitHub Copilot.**

## 2. Where the discussion stands

### 2.1 What I proposed first

1. **State as data, Markdown generated.**
   - Agents update the state through a CLI (`crf set …`), never by editing tables.
   - `crf render` regenerates `ORCHESTRATOR.md`, the status and the stack files.
   - `crf lint` reports precise errors.
   - An `events.jsonl` log allows resuming after a crash.
   - A variant keeps the state in the YAML front matter of `STATE.md`, validated by okf-schema
     (the user's own tool) and shown by the Studio as a properties table.
2. **No waiting done by an LLM.**
   - `crf ci wait` and `crf gate` run in the background and return 10–30 lines plus an exit
     code; the full log stays on disk.
   - Forge wrappers have pager and prompts disabled (`GH_PAGER=cat GH_PROMPT_DISABLED=1`,
     `GLAB_PAGER=cat GLAB_NO_PROMPT=true`).
3. **Compiled prompts** (`crf prompt driver 137`) instead of agents reading the full guideline.
4. **Three levels of orchestrator automation.** I recommended level 1.
   1. An LLM orchestrator fed by a `crf tick` digest.
   2. The intermediary itself orchestrates (`/loop` dynamic mode plus background notifications).
   3. A pure script that launches headless `claude -p` drivers.
5. **Interfaces.** Generated Markdown is enough; optional `crf dashboard` (HTML) or `crf watch`
   (terminal).

The user asked what `crf tick` and `crf prompt` do. I explained:

- **`crf tick`** reads the state, the run config (slots, stack order, dependencies) and a few live
  facts: git, one `gh` call, the window-test lock, driver heartbeats. It prints an action list
  (SPAWN / INTEGRATE / WAIT / STALE / LINT) for the orchestrator to act on. It never spawns
  agents: only an LLM can spawn sub-agents. An optional `--apply` would do only safe mechanical
  steps (create a worktree, render tables).
- **`crf prompt <role> <cr>`** assembles a ~1.5 KB prompt from:
  - a role card;
  - the CR's state (path, branch, base, round);
  - the project settings (gates, lock, commit format).

### 2.2 The user's pushback, accepted

The user said: "tout ça pour optimiser le guideline ? alors que l'agent va redécouvrir beaucoup
de choses (notamment le AGENTS.md qui est chargé dans le contexte)". In English: all this just to
optimise the guideline, when the agent rediscovers a lot anyway, AGENTS.md included.

**They are right.** The guideline is about 6k tokens. One cache write plus about 50 cached reads
is under $0.10 per agent. `AGENTS.md`, `CLAUDE.md` and the system prompt are a fixed cost anyway.
So `crf prompt` is **not a token lever**; it only buys correctness.

**What the measurements say.** The cost report is in the Studio repo, folder
`.agents/changes/01-inbox/cost-analysis/` (see §4). It covers 2026-10-19 → 26: 1,374 $ for 668
agents. The three cost drivers:

| Cost driver | Share |
| --- | --- |
| Long contexts re-read every turn (night orchestrator: 263k average context over 285 turns) | 40 % |
| Full cache rebuilds after waits longer than 5 minutes | 17 % |
| Files read through the shell and carried until the end (coder context grows 3.4×) | ~13 % |

**Revised short list:**

- Waits handled outside the LLM (the 17 %).
- A bounded orchestrator: a `tick` digest instead of raw git/gh/STATE output every turn, and a
  handoff past ~100k tokens (the 40 %).
- Summarised gate and CI outputs, with full logs on disk.
- Less rediscovery. This is a hand-over question, not a script question. Open points:
  - Round 2: resume the same coder, or start a fresh one with a hand-over note (files touched,
    where the logic is, pitfalls)?
  - Should the reviewer read only the diff and that note?

### 2.3 The user's latest direction, and my answer

The user wants **a design with very precise measurements** that works for **Claude Code and
GitHub Copilot**. My last message proposed four parts.

**1. Exact attribution by tagging.**
- Every spawned agent carries a mandatory tag at the head of its description and prompt, for
  example `[crf run=5 cr=137 task=- role=coder round=2 tool=claude-code]`.
- Today `roles.py` guesses roles with regular expressions over descriptions, which is imprecise.
- Measurement output is one row per agent turn:
  - run, CR, task, role, round, tool, model;
  - turn index, timestamp, gap since the previous turn;
  - input, cache read, cache write (5 min / 1 h), output;
  - a rebuild flag (write > 60 % of the context);
  - the estimated cost from a versioned price grid.
- Results are broken down by cold start, rebuild after a wait, context growth and output, and
  normalised by CR size (lines changed, files, tests added).
- **Quality guardrails** in every report: rounds used, reviewer verdicts, CI failures, CRs
  reopened after merge. A cost cut that adds rounds is not a gain.

**2. One measurement for both tools.**
- Claude Code: `analyze.py` reads `~/.claude/projects/**.jsonl`.
- Copilot: [copilot-session-usage](https://github.com/gsemet/copilot-session-usage) (the user's
  project, local checkout `/Users/az02065/Projects/DevTools/copilot-session-usage`) reads the
  VS Code Copilot debug logs and the Copilot CLI/App logs. It already breaks costs down per model
  and per sub-agent.
- Proposal: both produce the same row format. Best option is probably to add a Claude Code reader
  to `copilot-session-usage`.
- Units differ: Claude Code is tokens → $, Copilot is mostly premium requests × model multiplier.
  Probably measure both units.

**3. Reproducible experiments.**
- A bench of 6–8 archived CRs of different sizes and kinds.
- Each one is replayed from its base commit with the same request: current process against one
  variant.
- Compare cost by component, turns, rounds and quality (tests green, reviewer verdict, distance
  to the merged diff).
- Change one lever at a time.

**4. A cross-tool design.**
- **Shared core:** the state, the `uv run` scripts, role cards in neutral Markdown, the agent tag.
- **Claude Code adapter:** the skill, the Agent tool, background-task notifications.
- **Copilot adapter:** custom agents (`.agent.md`), prompt files, sub-agents.
- **First thing to verify:** whether Copilot supports nested sub-agents and background tasks that
  wake the agent. If not, the Copilot adapter must flatten the tree: a script takes part of the
  orchestrator role.

## 3. Open questions to the user (unanswered)

From my last message:

1. Which Copilot: VS Code agent mode, Copilot CLI, or both?
2. Cost unit for Copilot: estimated tokens/$, premium requests, or both?
3. Replay bench (precise, paid) or observation of real runs (free, noisy)? What budget, for
   example 8 CRs × 2 variants × 2 tools?
4. Is the mandatory agent tag acceptable, also for Copilot sub-agents?
5. Where does measurement live: a Claude Code reader added to `copilot-session-usage` as the
   common tool, or a script in the skill?
6. Which quality guardrails in each report? Proposed: rounds, reviewer verdicts, CI failures,
   reopened CRs.

Still open from earlier rounds:

7. What does the user mean by "dynamic workflows"? I assumed Claude Code's `/loop` dynamic mode
   (self-paced wake-ups) plus background-task notifications; not confirmed.
8. Where does the CR state live: front matter of `STATE.md` validated by okf-schema (my
   preference), or `cr.json` plus `run.json`?
9. Orchestrator automation level: level 1 recommended; does the user want to explore level 2?
10. Round 2+: continue the same coder, or a fresh coder with a hand-over note? Proposed to test
    both on the bench.
11. A CLI in the skill folder (`scripts/crf.py`, `uv run --script`), or a versioned package run
    with `uvx`? I prefer starting in the skill.

**Suggested next step once answered:** write a design document (change spec) for the measurement
layer first, then the levers, with a measurement plan per lever. Grill the remaining questions one
batch at a time, each with a recommended answer.

## 4. Sources to read (in this order)

| What | Path |
| --- | --- |
| The skill to improve | `/Users/az02065/Projects/DevTools/agentic-planning-surface/.claude/skills/change-request-factory/` (`SKILL.md` ~8 KB, `references/` ~62 KB) |
| The Studio guideline it should replace | `/Users/az02065/Projects/DevTools/markdown-okf-schema-studio/.agents/guidelines/change-requests-lifecycle.guidelines.md` (21 KB) |
| Cost report, French and English | `/Users/az02065/Projects/DevTools/markdown-okf-schema-studio/.agents/changes/01-inbox/cost-analysis/rapport-cout-orchestration.md` and `.en.md`; §6 lists 7 levers with measured bases |
| Cost scripts | same folder: `analyze.py` (reads `~/.claude/projects/**.jsonl`), `roles.py` (regex role guessing), `deep.py`, `rebuild.py`, `prs.tsv` |
| Copilot measurement tool | `/Users/az02065/Projects/DevTools/copilot-session-usage` (README, `src/`) |
| Live run state (a data source for measuring the current process) | `/Users/az02065/Projects/DevTools/markdown-okf-schema-studio/.agents/changes/03-requests/`: `RUN-BRIEF.md`, `RUN-BRIEF-addendum-run5.md`, `ORCHESTRATOR.md`, `135-…/TASKS.md`, each CR's `STATE.md` |
| This session's transcript | `/Users/az02065/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a.jsonl`, sub-agents under `…/dd375646-4450-4e52-a643-89ff1d9e405a/subagents/` (~2,270 files). Large: grep it, never read it whole. |
| User memory (preferences, rules) | `/Users/az02065/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/memory/MEMORY.md` |

## 5. Facts about the current factory, observed in this session's runs

These runs (2026-10-26/27, Studio repo) are good measurement material:

- **Run 2:** CRs 125–131, stack #139 (PRs #132–#138). Merged.
- **Run 3:** CRs 132–134, PRs #140–#142. Merged.
- **Run 4 / 5, still running when this was written** (orchestrator in the background of the old
  session):
  - CR 135 is one PR with 26 tasks (the whole performance and security audit), task drivers in
    parallel plus an integrator.
  - CRs 137–147 are stacked above it.
  - Do not interfere with it from the new session; read its files only.

What the runs showed:

- **No resume support.** An orchestrator died on an API error (403 ECONNRESET) and was restarted
  from files. That worked only because `TASKS.md` happened to exist: an argument for state as
  data plus an event log.
- **Stale tracking file.** `ORCHESTRATOR-STATUS.md` was hand-maintained and was stale after the
  restart.
- **Ad hoc scripts.** The main session wrote four ad hoc Python scripts to open batches of CRs
  (folders, `task.md`, `rules.md`, `STATE.md`, worktrees, table rows). That is the clearest
  candidate for a CLI command (`crf open`).
- **Permission denials.** The auto-mode classifier denies worktree, branch and remote-branch
  deletion ("Git Destructive"). The process must hand those commands to the user, never work
  around them. Landing should produce a ready-to-run cleanup script for the user.
- **Shared `node_modules` drift.** Worktrees symlink the main checkout's `node_modules`; that
  breaks when a CR adds a dependency (shiki). Per-worktree `npm ci` or a refreshed shared install
  is needed.
- **Real-window tests** are serialised by a `WINDOW-TESTS.lock` file.
- **Heavy CI** runs on demand on the top branch before announcing a stack.

## 6. User preferences and rules that apply

- Precedence: CONSTITUTION > AGENTS.md > guidelines > skills > harness reminders.
- Commit trailer `Assisted-by: Claude:<Model>`, never `Co-Authored-By`. English in all repo and
  forge artifacts. Always give links (PRs, CRs, runs, files) in reports.
- Never merge; never `git add -A`; never work around a permission denial; `\rm \cp \mv` (shell
  aliases are interactive); noclobber is on (`>|`).
- The orchestration rules:
  - Restart a stuck orchestrator; never do its work from the main session.
  - Note a blocked task and continue with the others.
  - At most 4 open PRs in parallel worktrees.
  - Stacked PRs with `gh stack`.
- `uv` against public repos: `UV_NO_CONFIG=1` (the corporate index is unreachable).
- `rtk` wraps shell commands and can hide test errors in summaries: verify with `rtk proxy`.
- The user wants options and a grill before building; questions should carry a recommended
  answer. They like short, plain reports.
- `agentic-planning-surface` has uncommitted user changes (README, `.gitignore`, `projects/`,
  deleted `need-defintion` files): never stage, revert or commit them.
