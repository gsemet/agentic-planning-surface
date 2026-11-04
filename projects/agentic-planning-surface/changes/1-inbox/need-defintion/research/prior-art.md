# Prior art

Captured 2026-10-23 (grill G8 in [02-user-answers.md](../02-user-answers.md)).
Scope of the comparison: **managing a backlog of ideas** shared by several developers and their
agents, kept out of the host's main branch, in Markdown. spec-kit is excluded on purpose: it
covers the CR execution phase, which another tool may take over.

Sources are web pages read on 2026-10-23 (READMEs, mirrors, third-party guides, release-note
aggregators). Details flagged *unconfirmed* need a check against the upstream repository.

## Summary

| Tool | Storage | Markdown | Off main | Multi-dev IDs | Agent-ready | Fit |
| --- | --- | --- | --- | --- | --- | --- |
| Backlog.md | `.md` files in the repo | Yes | Not documented | Numeric, collisions known | CLI `--json`, MCP | **Closest** |
| beads (`bd`) | JSONL + local Dolt DB | No | Sync branch *unconfirmed* | Hash IDs | `bd ready --json`, claim | Strong model, wrong format |
| git-bug | Git objects, no files | No | Yes (refs) | Yes | CLI, bridges | Wrong shape |
| Task Master | `tasks.json` | No | No | No | MCP | Wrong scope |
| Hosted issues (GitHub, GitLab) | Server | Partly | Yes | Yes | Through `gh` / `glab` | The "too far" baseline |

## Backlog.md (MrLesk/Backlog.md, MIT, TypeScript/Bun)

- Tasks are plain Markdown files in a project folder (`backlog/` by default; configurable with
  `backlog_directory` in `backlog.config.yml`), with drafts, decisions, docs, milestones and an
  archive. Fields: status, description, acceptance criteria, plan, definition of done,
  dependencies, comments.
- Built for agents: `backlog instructions overview`, `--json` on list commands, an MCP server,
  terminal Kanban and web UI.
- Git: optional `autoCommit`, plus `checkActiveBranches`, `remoteOperations`, `activeBranchDays`
  for a **cross-branch view** of tasks (a task edited on a feature branch is seen from others).
- IDs are prefixed numbers (`TASK-1`). Duplicate IDs across branches and processes were a real
  problem: v1.48.0 added duplicate detection and a `backlog doctor` repair flow, v1.50.1 makes ID
  allocation take a fresh remote snapshot first (per release-note aggregator).
- Its model is the opposite of ours: the backlog **lives in the code repository and travels with
  feature branches**. Keeping it on a separate branch is not documented.

What it tells us: the format (one Markdown file per item, front matter, CLI + MCP, agent
instructions command) is validated by a popular tool. Sequential numbering across developers is a
known trap. To test: point `backlog_directory` at a worktree of an orphan branch and check what
`autoCommit` and the cross-branch view do there.

## beads (steveyegge/beads, Go)

- A "distributed, git-backed graph issue tracker" for agents. JSONL is committed for sync; a local
  Dolt database (gitignored, rebuilt from JSONL on clone) serves queries.
- **Hash-based IDs** (`bd-a1b2`, sub-tasks `bd-abc.1`), introduced to avoid collisions across
  clones, branches and agents.
- Workflow verbs worth copying: `bd ready --json` (what can be worked on now, dependencies
  resolved), `bd update <id> --claim` (ownership), `bd dep add`, `bd sync` (export, commit, push).
- A `sync.branch` setting to keep issue data on a separate branch appears in a third-party skill
  page (*unconfirmed*).

What it tells us: hash or slug IDs, an explicit claim, and a "ready" query answer the multi-dev
core. But the data is JSONL, not readable rich Markdown, so it does not fit G6 (Markdown
everywhere) nor the rich per-item folders (notes, grill, attachments).

## git-bug (MichaelMure/git-bug, GPLv3, Go)

- Issues and comments stored as git objects, not as files; pushed and pulled through the existing
  remote; CLI, TUI, web UI, bridges to GitHub and GitLab.

What it tells us: storing planning in git without touching the working tree is possible, but the
data is not browsable Markdown and agents cannot edit it with their file tools.

## Task Master (eyaltoledano/claude-task-master)

- Parses a PRD into `.taskmaster/tasks/tasks.json` (tasks, dependencies, priorities, test
  strategies) with an LLM; needs an API key; MCP server.

What it tells us: it decomposes one PRD into tasks for one developer. It is a CR-phase tool, not a
shared backlog of ideas.

## Hosted issues (GitHub Issues/Projects, GitLab issues/boards)

- Already multi-developer, off main, linked to PRs, readable by non-developers; agents can use
  them through `gh` / `glab`.

Devil's advocate: this is the baseline to beat. The user's objection (A1) is distance: no local
Markdown, one network call per read, no rich folders. A local cache synced with issues would
answer that too; it stays out of scope but is a real alternative.

## Open points raised by the study

- Is our need "Backlog.md, but on an orphan branch and safe across developers"? If yes, extending
  or wrapping Backlog.md may beat writing `aps`.
- Item IDs: adopt hash or slug IDs (beads) instead of sequential numbers (Backlog.md's trap).
- Per-item content: a single Markdown file (Backlog.md) or a folder per item (today's layout)?

Sources:

- [Backlog.md README](https://cdn.jsdelivr.net/gh/MrLesk/Backlog.md@main/README.md)
- [Backlog.md v1.48.0 release](https://newreleases.io/project/github/MrLesk/Backlog.md/release/v1.48.0)
- [Backlog.md v1.50.1 release](https://newreleases.io/project/github/MrLesk/Backlog.md/release/v1.50.1)
- [beads technical guide](https://brenner-axiom.codeberg.page/beads-technical-guide/)
- [beads introduction](https://www.mintlify.com/steveyegge/beads/introduction)
- [beads skill page (sync branch)](https://skills.cat/skills/itechmeat/llm-code/beads)
- [git-bug mirror](https://github.com/digi-lab/git-bug)
- [Task Master README](https://cdn.jsdelivr.net/npm/task-master-ai-notion@0.26.0/README-task-master.md)

## Update after the model inversion (grill G40, round 16)

The need is now an **out-of-project planning surface**: one planning repository for N code
repositories and N users, with folder-per-idea lifecycle (`01-inbox` → `04-archives`), a PO
triage, one developer per taken idea, and code worktrees created under the surface.

| Tool / pattern | Out of project | Multi-project | Folder per idea | Lifecycle by folders | PO triage | Code worktrees |
| --- | --- | --- | --- | --- | --- | --- |
| Our scenario | Yes | Yes | Yes | Yes | Yes | Yes (`aps workspace`) |
| beads contributor mode | Yes (`~/.beads-planning`) | No (per repo) | No (JSONL) | No (statuses) | No | No |
| Backlog.md | No (in repo) | No | No (one file) | No (statuses) | No | No |
| Vibe Kanban | Yes (app DB) | Yes (workspace = N repos) | No | Kanban columns | No | **Yes, per task** |
| repo-of-repos pattern | Yes | Yes (front matter lists repos) | Plans as files | No tooling | No | Inner repos |
| meta-repo pattern | Yes (`repos.yaml`) | Yes | — | Delegated to a tracker | Tracker | — |
| planning-with-files, repo-todo | No (in repo / ignored) | No | Per task | No | No | No |

- **beads contributor mode**: `bd init --contributor` routes planning issues to a separate store
  (`~/.beads-planning`) so they stay out of pull requests; routing is chosen from the git remote
  (SSH = maintainer → `./.beads/`, HTTPS fork = contributor). `BEADS_DIR` points the database
  anywhere. Out of project, but per user and per repo, not a shared multi-project surface.
- **Vibe Kanban** (BloopAI): a Kanban app that runs coding agents in parallel; each task gets a
  workspace of one or more repositories, each as a git worktree on its own branch, stored in
  `.vibe-kanban-workspaces`. Closest to our steps 6–7 (execution), not to the Markdown definition
  phase; its state is in the app, not in versioned Markdown.
- **repo-of-repos / meta-repo patterns** (blog posts): a root workspace repository holds plans as
  Markdown with front matter listing the inner repositories each plan touches ("plans always live
  in repo-of-repos, never inside an inner repo"), or a `repos.yaml` manifest plus `AGENTS.md`.
  Closest in **shape** to our surface, but a convention, with no lifecycle tool.

Conclusion: the shape (planning repository above N code repositories) is an emerging pattern;
no tool found implements it with a Markdown folder-per-idea lifecycle, PO triage and shared
multi-user sync. The pieces exist separately: beads (IDs, claim, out-of-repo store), Backlog.md
(Markdown + CLI + agent instructions), Vibe Kanban (worktree per task, multi-repo).

More sources:

- [beads contributor mode](https://www.mintlify.com/steveyegge/beads/guides/contributor-mode)
- [Vibe Kanban — repositories](https://vibekanban.com/docs/workspaces/repositories)
- [Vibe Kanban — creating workspaces](https://vibekanban.com/docs/workspaces/creating-workspaces)
- [Repo-of-repos pattern](https://raffertyuy.com/raztype/repo-of-repos-pattern/)
- [Agents meta-repo pattern](https://seylox.github.io/2026/03/05/blog-agents-meta-repo-pattern.html)
- [Multi-repo workspace strategy](https://medium.com/@sunghyunroh/multi-repo-workspace-strategy-the-structure-where-ai-coding-agents-actually-shine-4ed6b87fb11d)
- [repo-todo](https://github.com/smhanov/repo-todo)
- [planning-with-files](https://github.com/othmanadi/planning-with-files)

## Backlog.md on its own backlog (2026-10-25, round 33)

The user's reading of [Backlog.md's `backlog/` folder](https://github.com/MrLesk/Backlog.md/tree/main/backlog),
which the tool uses for its own development, checked with the GitHub API on 2026-10-25:

- Folders: `tasks/` (167 files), `drafts/` (16), `completed/`, `archive/`, `decisions/`,
  `docs/`, `milestones/`, `assets/`, `config.yml`.
- **One change = one Markdown file.** Task files range from 1 KB to 39 KB, median 5 KB. A task is
  either as small as an intent or, once it holds the spec to implement, a long single file.
  There is no place in between to study, prototype or grill: no research notes, mock-ups or
  decision log next to the item. `drafts/` is a stage before `tasks/`, still one file per item.
- **Project rules live in the planning folder.** `decisions/` (ADRs such as `decision-1 - Use
  Tailwind CSS v4…`) and `docs/` (`doc-001 - Testing Style Guide`…) belong to the code project's
  harness. A coding agent that does not go through Backlog.md never sees them, or every change
  must use that workflow.
- **IDs are not padded**: `back-200`, `back-743.1`, `decision-1`, while docs are padded
  (`doc-001`). Sorted by name, `back-100` comes before `back-2`.
- **ID collisions across branches**: tasks `back-760.1` "Reserve task IDs in records shared by
  every branch and worktree" and `back-760.2` "Make assignment exclusive across branches and
  worktrees" show the problem G110 avoids by taking `NNN` only at landing.

How the surface answers each point:

| Backlog.md | Surface |
| --- | --- |
| one file per change | **one folder per idea** that grows: `01-intent.md`, then grills in `02-user-answers.md`, `research/`, `prototypes/`, then `03-change-spec.md` (G14, G28, G116) |
| `decisions/` and `docs/` in the planning folder | rules, ADRs and the final spec go **into the target project** (its `AGENTS.md`, constitution, docs), so every agent sees them; the surface keeps only planning material (G104, G117) |
| `back-1` … `back-760` | slug as the ID; `NNN` three digits, zero-padded, taken at landing (G71, G118) |
