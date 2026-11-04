# Need definition — agentic planning surface

Status: initial intent, captured 2026-10-23 from a working session on another project. Nothing is
designed or decided yet beyond what is written here. This file is self-contained: it does not
assume any knowledge of the project it came from.

## 1. Context

AI coding agents (one main session talking to the user, plus sub-agents) deliver work on a code
repository through a file-based workflow:

- **Backlog item**: an idea, bug or request not yet scheduled, one folder per item, grouped by
  priority (`backlog/P1|P2|P3/<slug>/`), indexed by `backlog/INDEX.md`.
- **Change request (CR)**: one unit of delivered work = one branch = one pull request with green
  CI. Numbered `NNN` in landing order.
- **PRD folder**: the working folder of a CR in progress, `requests/NNN-<slug>/`, with
  `00-request.md` (intent + user decisions), `task.md` (brief), `rules.md` (hard rules for
  sub-agents), `STATE.md` (status header + step checklist), `reports/T1-r<n>.md` (coder report
  per round), `reviews/T1-r<n>.md` (reviewer verdict per round).
- **Archive**: a landed CR, `archives/NNN-<slug>/`, the PRD folder plus a `report.md`.
- **Orchestration files**: a CR table and a status file rebuilt from every CR's `STATE.md` header
  when several CRs run in parallel (one orchestrator agent, one driver agent per CR, coder and
  reviewer agents per round).

All of this lives today in `.agents/changes/` inside the code repository, ignored by git. It is
the agents' shared working memory and the only source of truth to resume work in a new session.

## 2. Problem

- The folder is **not versioned**: no history of decisions, no way to see what changed when, no
  backup, no sharing between machines or sessions, nothing to link from a PR.
- It **must not be merged into the code repository's main branch**: it is planning material, not
  product code, and it should not trigger CI or be subject to the code repository's branch rules.
- It **grows without bound**: archives accumulate heavy, low-value files (packaged builds, raw
  test-campaign outputs, traces, videos, duplicated screenshots). One project reached 1.7 GB, most
  of it in a single archive.
- **Many agents write at the same time** (parallel CRs, each with a driver, a coder and a
  reviewer), so any versioning scheme must survive concurrent writers in one working copy.
- Repetitive mechanics are done by hand by agents (moving folders, ticking steps, rebuilding the
  status file, cleaning worktree symlinks) and they make avoidable mistakes: interactive shell
  aliases (`rm -i`) hanging a background command, stale status files, a CR exceeding its round
  limit unnoticed, landings forgotten.

## 3. Goal

A **dedicated, generic Python CLI** that turns this planning folder into a versioned **planning
surface** that lives in its own repository, attached to any code project, usable by humans and by
AI agents. It is not tied to any language, framework or product of the host project.

## 4. Requirements (initial)

### 4.1 Storage and attachment

- The planning surface is its **own git repository** (one per host project is the default; a
  shared repository with one folder per project is an option to evaluate).
- It is **attached** to a host project by checking it out into the host's planning folder
  (default `.agents/changes/`), which the host ignores in git. Attaching on a fresh clone of the
  host is one command.
- The planning repository has **no CI and no branch protection** by default; nothing in it may
  trigger the host project's CI.
- The planning content may be **public**; the tool must make that explicit and help keep secrets
  and internal data out (see 4.4).

### 4.2 Every change is committed

- Every meaningful change of the plan is a commit in the planning repository: backlog item added
  or split, grill decisions recorded, CR opened, brief written, each round's report and review,
  each `STATE.md` transition, PR opened, CI result, landing/archive.
- **Concurrency-safe**: each writer commits only its own paths (pathspec commits), so parallel
  agents never commit each other's files; a busy `index.lock` is retried, never forced.
- Commit messages follow one readable convention, for example `plan(NNN): step 8 PR #34 opened`
  or `plan(backlog): grill 031–040`, so the log is a journal of the work.
- **Push policy**: pushes are batched (for example on each orchestrator tick and after each user
  interaction), with `pull --rebase` first; paths are disjoint, so conflicts should not happen and
  must be reported clearly if they do.
- References to the host project's PRs, branches and commits are written in a form that links
  across repositories (`owner/repo#n`).

### 4.3 Structure and state as data

- The tool knows the layout (backlog, requests, archives, orchestration files) and can create,
  validate and move items: open a CR from a backlog item (including a partial split), land a CR
  into the archive, keep the index in sync, take the next free `NNN`.
- `STATE.md` has a **machine-readable header** (driver/owner lock, last update time, status,
  step, round n/limit, head commit, PR, CI run and result, next action, open question) that the
  tool reads and writes; the human-readable checklist stays.
- The tool can **rebuild the orchestration status** from all headers, and report: stale owners
  (no update for a configurable time), CRs over their round limit, ready/blocked CRs, open PR
  count against a cap.

### 4.4 Hygiene and cleanup

- A **size and content policy** for the planning repository: ignored file types (packaged builds,
  videos, traces, raw campaign outputs, archives of archives), a maximum file size, a maximum
  archive size.
- A **clean** command that applies the policy to existing archives (dry run first), and a check
  that blocks committing content that violates it.
- A **sensitive-content check** before commit/push (tokens, internal hostnames, e-mail addresses,
  paths or names the user lists), because the planning surface may be public.
- A one-time **import** of an existing, unversioned planning folder: clean it, then make the
  first commit.

### 4.5 Usable by agents

- Every command is **non-interactive** by default (no prompt, no pager, no editor), with a clear
  exit code and a short, parseable output (`--json`).
- Commands never wait on input and never run longer than a short bound; long waits are the
  caller's job.
- The tool can print the instructions an agent needs (layout, rules, commit convention) so a
  workflow guideline can point to it instead of duplicating it.

### 4.6 Packaging

- Python CLI, installable and runnable with `uv` (`uvx <tool>` / `uv tool install`), no runtime
  dependency on the host project's stack.
- Works on macOS and Linux; Windows is a nice-to-have.
- Tested (unit tests on a temporary git repository), documented (README with the commands and
  the layout).

## 5. Out of scope (for now)

- Driving the agents themselves (starting sub-agents, scheduling), and CI watching: the tool
  manages the planning data, not the agents' runtime.
- Hosting-specific features beyond reading PR/CI state for the status report (to be decided:
  GitHub first, others later?).
- Merging host pull requests, or any action on the host repository's branches.

## 6. Open questions for the grill

1. One planning repository per host project, or one shared repository with a folder per project?
2. Attach by `git clone` into the planning folder, or by `git worktree` of a branch? Which one is
   the default, and is the other supported?
3. Who commits what: does every agent call the tool for its own files, or does only the
   orchestrating agent commit on its behalf? What is the push cadence?
4. File format of the machine-readable `STATE.md` header: the current one-line key/value style,
   YAML front matter, or a sidecar `state.yml`?
5. Size policy defaults: maximum file size, maximum archive size, ignored types.
6. Does the tool read PR and CI state from the hosting service (needs a token), or only store what
   agents write?
7. Name of the CLI command and of the default planning folder.
