# Need definition — user answers

Status: user answers captured 2026-10-23, following [01-intent.md](01-intent.md). Each answer is
followed by what it implies for the design. Items marked **proposed** are the agent's
recommendations, not yet validated by the user.

## A1. Audience and positioning

**User answer**: any developer, on GitHub or GitLab. The goal is to keep rich planning Markdown
without committing it to the host's main branch, because that causes too many problems (heavy
pipelines, pollution of the code history). Planning should ideally live in a dedicated tool (Jira,
...), but such tools are too far from the agents: agents need local Markdown to be efficient.

Implications:

- The tool is a **public, general-purpose product**, not a personal script: generic layout,
  documented configuration, no assumption about one user's habits or machine.
- **Hosting-agnostic** from day one: GitHub and GitLab are both first-class. Any hosting feature
  (PR/MR links, CI state) goes through an adapter; the core only needs a plain git remote.
- Cross-repository references must support both forms: `owner/repo#n` (GitHub PR) and
  `group/project!n` (GitLab MR).
- Positioning: a **local-first planning layer for agents**, the bridge between the code
  repository and a remote tracker. Syncing with Jira or GitHub/GitLab issues stays out of scope
  for now, but nothing in the layout should prevent it later (stable IDs, machine-readable state).
- The planning repository may be public: the sensitive-content check (intent 4.4) is a core
  feature, not an option.

## A2. Concurrency: several developers

**User answer**: yes, concurrency must be handled with several developers, each running their own
agents (for example several Claude Code users on the same project).

Implications — concurrency has two levels:

1. **Inside one working copy**: several agents of one developer write at the same time. Pathspec
   commits and `index.lock` retry (intent 4.2) cover this.
2. **Across clones**: several developers push to the same planning remote. This is a real
   distributed problem, and it makes some of today's files conflict-prone:
   - **`NNN` allocation**: two developers opening a CR at the same time both take the next free
     number. Needs a decision (see Q-A below).
   - **Shared index files** (backlog index, CR table, orchestration status): edited by everyone,
     they conflict on every rebase. **Proposed**: these files are **generated** by the tool from
     per-item data (each backlog item and each CR carries its own metadata), never hand-edited,
     and either not committed or regenerated after each rebase.
   - **Ownership**: the driver/owner lock in the `STATE.md` header must identify a developer and
     a machine, not only an agent name, so another developer's tool knows a CR is taken.
     **Proposed**: an advisory lease with an expiry time; a stale lease is reported, and taking
     it over is an explicit command.
   - **Push**: `pull --rebase` then push, retried a bounded number of times on rejection. Because
     other agents may be writing in the same working copy, the pull must not disturb their
     uncommitted files. Mechanism to be decided at design time.

## A3. Format of the state header

**User answer**: take inspiration from an existing project that uses this workflow, without
referencing it directly.

Observed in that project (inspiration only):

- `STATE.md` starts with a 4-line header of `key: value` pairs separated by `·`:
  `driver` + `updated`, `status` + `step` + `round n/limit`, `head` + `PR` + `run`,
  `next` + `question`. Then a one-line checklist of numbered steps (`[x] 1 Pick · [ ] 2 Grill ·
  ...` up to `11 Land`).
- The `updated` field holds only a time (`11:22`), no date and no time zone: not usable to detect
  stale owners across days or across developers.
- The backlog index is a hand-edited table (priority, item, folder) mixing open items, landed
  items and free-text decisions; the CR table and the status file are also hand-edited.

**Proposed**:

- YAML front matter at the top of `STATE.md`, with an ISO 8601 timestamp with time zone, a
  developer identity, and the same fields as today. The checklist stays as Markdown below it.
- The list of steps and statuses is **configurable** (the tool ships the current 11-step flow as
  the default), since other teams will have their own flow.
- Free-text decisions move out of the index into their own file, so the index can be generated.

## A4. Name

**User answer**: the project is `agentic-planning-surface`, the CLI command is `aps`.

- Package name on PyPI: `agentic-planning-surface`; entry point `aps`; run with
  `uvx --from agentic-planning-surface aps ...` or `uv tool install agentic-planning-surface`.
- **To check**: `aps` is not already taken on PyPI or by a common system command.
- Default planning folder: `.agents/changes/` (from the intent; not discussed yet).

## Questions for the next round

- **Q-A, `NNN` numbering across developers**: (a) reserve a number by pushing a reservation
  commit first (the push is the lock), (b) give a CR a stable non-numeric ID (slug, or slug + short
  hash) and assign `NNN` only at landing, in landing order, or (c) drop `NNN` entirely.
  **Proposed**: (b), since landing order is what `NNN` means today and landing is a single,
  serial event.
- **Q-B, generated index files**: commit them (readable on the hosting web UI, but regenerated
  after each rebase) or keep them local only (no conflicts, not visible online)?
- **Q-C, one planning repository per host, or shared**: still open from the intent; the
  multi-developer answer favours one repository per host project.
- **Q-D, attach mode**: `git clone` into the planning folder (recommended in round 1), plus how
  agents in host worktrees reach the planning folder (symlink managed by `aps`, environment
  variable, or lookup of the main checkout).
- **Q-E, hosting state**: does `aps` read PR/MR and CI state itself (through `gh` / `glab` when
  present), or only store what agents write?
- **Q-F, v1 scope**: proposed first slice = attach, commit, push, check (size + secrets), clean,
  import; second slice = CR lifecycle (open, land), state header, status report.

## Grill log

Devil's-advocate questions asked to the user, one round at a time, with the answers and what they
change. Started 2026-10-23, after the round-1 answers above.

### Round 1

| # | Question | Answer |
| --- | --- | --- |
| G1 | Why not adopt or extend an existing tool (beads `bd`, Backlog.md, Task Master, spec-kit)? | The user does not know them yet. |
| G2 | Separate repository, or an orphan `plan` branch in the host repository? | **Orphan branch**. |
| G3 | If only one pain could be solved, which one? | **Multi-developer collaboration**. |
| G4 | Who reads the planning surface? | **Mostly agents**; humans occasionally. |

What changes:

- **G1**: a comparative study of existing tools is needed before designing anything, to decide
  build, extend or adopt.
- **G2 reverses the intent's default** (separate repository, `git clone`). The default attach
  mode becomes an orphan branch of the host repository, checked out in the planning folder (for
  example with `git worktree`). Consequences to handle: the host CI must not run on that branch,
  and the host's branch rules must not apply to it; the planning content has the same visibility
  as the code (no public planning for a private codebase).
- **G3**: concurrency across clones is the core problem, not an add-on. `NNN` allocation,
  shared index files and ownership (see 02, A2) are first-slice topics.
- **G4**: the format can favour machine reading. This questions the choice of Markdown as the
  storage format for state (see round 2).

### Round 2

| # | Question | Answer |
| --- | --- | --- |
| G5 | How to keep the host CI off the orphan branch? | **A filter in the host CI configuration** (one-time change on main). |
| G6 | Agents are the main readers: why Markdown for state, not JSONL/SQLite like beads? | **Markdown everywhere.** |
| G7 | How often do two developers touch the same CR or backlog item? | **Never: one CR = one developer.** |
| G8 | Run the prior-art study now? | Yes, but not spec-kit. **The need is a way to manage the backlog of ideas**; once a CR starts, spec-kit or another tool can take over. |

What changes:

- **G8 narrows the scope sharply.** The core is the **backlog of ideas** (capture, prioritise,
  grill, split, pick), shared across developers and agents. The CR execution machinery of the
  intent (rounds, reports, reviews, driver locks, orchestration status) is no longer the core: it
  may be delegated to another tool once a CR starts. To confirm: does the planning surface still
  keep the CR folders and archives, or only a link to them?
- **G5**: `aps` can generate or print the CI filter snippet for GitHub Actions and GitLab CI, but
  the host's CI file is changed by the user, once.
- **G6**: state stays in Markdown (front matter for machine fields). Merge safety must then come
  from the layout (one file per item, generated indexes), not from the format.
- **G7**: no concurrent editing of one item. Conflicts are limited to shared files (index,
  numbering) and to ownership transfer, which can stay simple.

### Round 3

Prior-art study: [research/prior-art.md](research/prior-art.md).

| # | Question | Answer |
| --- | --- | --- |
| G9 | Is the need just "Backlog.md on an orphan branch, multi-dev safe"? | **No: items need folders**, not one file per task. |
| G10 | What is an "idea", concretely? | An idea that **matures and becomes a CR**. A CR starts with an intent, the idea is grilled, then a spec is written, with a prototype or mock-up, then coding starts (directly, spec-kit, OpenSpec, ...). |
| G11 | Which lifecycle transitions must the tool support? | **All four**: capture, grill/refine, prioritise/split, take/give back. |
| G12 | When another tool takes over a CR, what does the planning surface keep? | **The CR folder too**, until it is archived. |

What changes:

- **G10 defines the lifecycle**: idea → intent → grill → spec (+ prototype / mock-up) → coding
  (handed to a coding workflow: direct, spec-kit, OpenSpec, ...) → landed → archived. The
  planning surface owns everything **before coding** and keeps the CR folder during and after.
- **G8 + G12 together**: the scope is not "backlog only". It is the full folder of a change, but
  the tool does not drive the coding phase; it hosts its files.
- **G9**: an item is a folder (intent, grill log, spec, prototypes, attachments), which rules out
  adopting Backlog.md as is. Its conventions (front matter, `--json`, MCP, instructions command)
  remain good inspiration.
- **G11**: the four transitions are the functional core of the first version.

### Round 4

| # | Question | Answer |
| --- | --- | --- |
| G13 | Handoff of the spec to spec-kit / OpenSpec (which expect specs on main)? | **Later.** The point is a **rich definition surface**: a folder per idea with several Markdown files, diagrams, ideas, mock-ups, that agents and humans can view and edit (the purpose of the user's rich Markdown editor, markdown-okf-schema-studio). The output is the precise spec for the coding agent; its handoff is decided later. |
| G14 | Where do prototypes and mock-ups live? | **In the idea's folder.** |
| G15 | Idea → CR: same folder or two objects? | **Same folder**: the state changes, the folder does not. |
| G16 | Who decides priority across developers? | **One person decides** (lead / PO role); others propose. |

What changes:

- **G13 reframes the product**: a *definition surface*, a set of rich, editable Markdown folders,
  viewed and edited by humans in a rich editor and by agents with file tools. Spec handoff to a
  coding workflow is out of scope for now.
- **G13 vs G4**: humans are not occasional readers, they are **co-authors** (through the editor).
  Commits must then also capture human edits, not only agent calls (round 5).
- **G14 vs the 1.7 GB problem**: heavy files are allowed in the idea folder, so the size policy
  must distinguish useful sources (mock-ups, diagrams) from derived or bulky outputs, and the
  limits are a hard guard, not a filter by file type only.
- **G15**: a stable folder whose state lives in its front matter. A layout that encodes state or
  priority in the path (`backlog/P1/<slug>/`, `requests/` → `archives/`) means moves, broken links
  and conflicts; to challenge in round 5.
- **G16**: priority is a single-writer field; developers capture ideas without a priority, the
  decider triages them.

### Round 5

| # | Question | Answer |
| --- | --- | --- |
| G17 | Who commits a human edit made in the Studio, and when? | **Left open**: the user does not know yet. |
| G18 | Keep state and priority in the path (`backlog/P1/<slug>/`, `requests/` → `archives/`)? | **Keep the folders**; links must be **fixed automatically** on each move. |
| G19 | Stable, collision-free ID for an idea? | **Slug only.** |
| G20 | Which human interfaces must work? | **All**: the Studio (VS Code), GitHub/GitLab web, any editor, and a view generated by `aps`. |

What changes:

- **G17** stays an open question for the design phase. Candidates: Studio integration, a watch
  daemon, an explicit save command, or a commit by the next `aps` call.
- **G18**: moving folders is a core, tool-owned operation (`aps move`, or implicit in `aps take`,
  `aps land`, `aps prioritise`), and it rewrites every relative link that points into or out of
  the moved folder. Since the path encodes state, ID = slug must stay unique across all state
  folders, not only within one.
- **G19**: slug collisions between developers are detected by `aps` (locally across all folders,
  and on push), not prevented by construction.
- **G20**: the Markdown must render correctly on GitHub and GitLab and in plain editors; no
  Studio-only syntax is required to read an item. The generated view is a fourth target.

### Round 6

| # | Question | Answer |
| --- | --- | --- |
| G21 | Which links are fixed on a move? | **Internal links only**; external links may break. |
| G22 | Required content of an idea folder? | `01-intent.md`, `02-user-answers.md`, `03-change-spec.md`. Optional sub-folders: `prototypes/`, `intake/` (when the request comes from Jira, for example). More can be added later. |
| G23 | Orphan branch: external contributors need push rights on the host. | **That is what bothers the user: a sidecar project is simpler to clean and to manage.** |
| G24 | Which state folders? | **All four, with a numeric prefix**: `01-inbox`, backlog (P1/P2/P3), requests, archives (including abandoned). |

What changes:

- **G23 reverses G2**: the default goes back to a **sidecar repository** (as in the intent).
  The host CI filter (G5) is no longer needed by default. To confirm in round 7: is the orphan
  branch dropped or kept as an option?
- **G24**: layout `01-inbox/`, `02-backlog/P1|P2|P3/`, `03-requests/`, `04-archives/`. The
  numeric prefix gives the reading order in any file explorer.
- **G22**: a fixed, small template; `aps` creates it and `aps check` reports missing files. Note:
  this need-definition folder was aligned in round 7 (grill merged here, study in `research/`).

### Round 7

| # | Question | Answer |
| --- | --- | --- |
| G25 | One sidecar per host repository, or one shared by several? | **One per team / product**, covering several code repositories. |
| G26 | How does an agent in the host find its sidecar, even on a fresh clone? | **Local config only** (`aps attach <url>`), nothing committed on the host's main. |
| G27 | May the sidecar history be rewritten to purge big files? | **No: prevention only.** The size policy blocks before commit; cleaning touches the current tree only. |
| G28 | This folder does not follow the G22 template. | The grill **is** the user answers: merged into this file. Prior art and research go to **dedicated sub-folders**. |

What changes:

- **G23 + G25 settle storage**: a sidecar repository per team or product. Each idea declares the
  code repositories it touches (one or several); cross-repository ideas are first-class. The
  orphan-branch mode is dropped as a default.
- **G26**: `aps attach` must be quick to run on a fresh clone and must tell the agent clearly
  when no sidecar is attached. Several host repositories point to the same sidecar, so one local
  checkout of the sidecar may serve several host clones (to decide: shared checkout or one per
  host).
- **G27**: since history is never rewritten, the pre-commit guard is the only protection against
  growth: it must run on every commit path (`aps` and raw `git`, through a hook).
- **G28**: template extended with optional `research/` (and, by extension, any dedicated
  sub-folder). This folder now follows it: `01-intent.md`, `02-user-answers.md`,
  `research/prior-art.md`; `03-change-spec.md` comes at the end of the grill.

### Round 8

| # | Question | Answer |
| --- | --- | --- |
| G29 | Where does the sidecar checkout live on a developer machine? | A **worktree of a sub-folder** of the planning repository, created from **one central checkout**, so the progress of each project is easy to manage; a full checkout stays possible to link across teams. Not fully clear yet: to challenge with concrete examples (round 9). |
| G30 | Do orchestration files (CR table, tick status, test locks) belong in the shared repository? | **Only the state of each CR.** Tick status and locks stay local. |
| G31 | Is execution control (`STATE.md` header, rounds, stale owner) part of `aps`? | **No, out of scope.** |
| G32 | One commit per change means hundreds of commits a day. | **Like Obsidian (Git plugin)**: a small **hysteresis** before committing, which points to `aps save` and `aps watch`. |

What changes:

- **G29**: the sidecar layout is one folder per project (`<project>/01-inbox`, ...), and each host
  sees its own project's folder. Mechanism to settle in round 9.
- **G30 + G31** shrink the data model: per CR, `aps` stores a lifecycle state (the folder it is
  in, plus a few front-matter fields such as owner and links to branch / PR). Rounds, reports and
  reviews are files the coding workflow writes; `aps` versions them but does not interpret them.
- **G32 answers G17** in part: `aps watch` commits after a quiet delay (debounce), `aps save`
  commits now. Human edits in any editor are captured by the watcher.

### Round 9

| # | Question | Answer |
| --- | --- | --- |
| G33 | Which checkout layout (A shared clone + symlinks, B detached sparse worktree, C branch per project, D full clone per host)? | **B: detached worktree + sparse checkout.** |
| G34 | Where does an idea touching several repositories live? | **In a `_shared/` folder.** |
| G35 | Can one host repository belong to several sidecars? | **No: one host = one sidecar.** |

What changes:

- **G33 fixes the attach model**:
  - one central clone of the sidecar per machine (for example `~/.aps/acme-planning.git`);
  - each host gets a `git worktree add --detach` of it in `.agents/changes/`, with a sparse
    checkout of `<project>/` and `_shared/` (G34);
  - `aps save` commits locally in that worktree, then rebases on `origin/main` and pushes
    `HEAD:main`; worktrees never hold a branch, so no "branch already checked out" clash;
  - all worktrees share one object store, so `fetch` is done once per machine.
- Consequences to handle: local commits not yet pushed live on a detached HEAD, so `aps` must
  never drop them (push or warn); links to other projects' folders are absent from disk (only
  `_shared/` and the own project are present).
- **G35**: the local config of a host stores one sidecar URL and one project name.

### Round 10

| # | Question | Answer |
| --- | --- | --- |
| G36 | How does an agent in a host worktree (`studio-wt-041/`) reach the plan? | **One plan worktree per host worktree** (detached, sparse, pushes `HEAD:main`). |
| G37 | Default `aps watch` timings? | **Commit after 30 s of quiet, push every 2 min.** |
| G38 | Rebase conflict before push? | **Conflict copy** (Dropbox / Obsidian style): keep the remote version, write ours to `<file>.conflict-<dev>.md`, push, report. Nothing blocks, nothing is lost. |
| G39 | Offline work? | **Normal case**: commits pile up locally and go out on reconnect; `aps status` shows how many are pending. |

What changes:

- **G36**: a machine may hold many plan worktrees of the same sidecar (one per host checkout and
  per host worktree). They only see each other's changes through push and pull, so `aps watch`
  must also **pull** regularly, not only push. `aps` must create the plan worktree when a host
  worktree is created and remove it with the host worktree (today's symlink-cleaning chore).
- **G38**: conflict copies are tracked files; `aps check` lists unresolved ones.
- **G39**: the detached HEAD with unpushed commits is a normal, long-lived state, so pending
  commits must be protected from `git worktree remove` and from garbage collection.

### Round 11 — the model is inverted

| # | Question | Answer |
| --- | --- | --- |
| G40 | Who runs `aps watch` when a machine holds many plan worktrees? | **The question is upside down.** The worktree inside the host has no real reason to exist. What matters is a **planning project** (this surface) that **targets N projects**. It contains `projects/` that point to their repository on GitHub or GitLab, and ideas are grilled there. Agents clone the code repositories themselves (and create their own study worktrees). The planning surface is **multi-project and multi-user by default**, which also makes cross-project links simple. Optional **single-project mode**: sparse checkout of the right sub-folder into the host's `.agents/changes/`. |
| G41 | The watch pulls while a file is open in the Studio. | **The editor reloads** the file (it already handles on-disk changes). |
| G42 | Is the team sidecar public or private? | **Configurable** (`visibility: public|private` drives the strength of the sensitive-content check). |
| G43 | Where is the generated view published? | **Pages with a light CI** in the planning repository, only to publish the view. |

What changes — G40 is the biggest decision of the grill so far:

- **Default model**: the developer (and their main agent session) works **in the planning
  repository**, not in a code repository. It holds `projects/<name>/` (each with its remote URL
  and the lifecycle folders `01-inbox/` ... `04-archives/`) and `_shared/` for cross-project
  ideas (G34). Agents clone or create worktrees of the code repositories when they need them.
- **Made obsolete or optional by G40**: the plan worktree per host worktree (G36), the detached
  sparse worktree in each host (G33, now the single-project mode only), the host-side discovery
  config (G26, single-project mode only), the CI filter on the host (G5).
- **Simplified**: one working copy of the plan per machine, so one `aps watch` per machine, no
  symlinks, all project folders present on disk (internal links always resolve).
- **G43 vs intent 4.1** ("no CI in the planning repository"): a light, publish-only CI is now
  accepted.

### Round 12

| # | Question | Answer |
| --- | --- | --- |
| G44 | Where do agents clone the code repositories? | **`projects/<name>/.worktrees/<unique-name>/`**, git-ignored. |
| G45 | A session opened in the surface does not load the code repository's `CLAUDE.md`, skills or hooks. How is coding done? | **A separate session in the clone.** |
| G46 | What is `aps`'s own value, beyond "a git repo of Markdown + Obsidian Git"? | **Lifecycle only** is indispensable (capture, triage, take, land, abandon, with folder moves and link rewriting). Sync, guards and the project registry were not ticked. |
| G47 | Is a raw idea captured by one developer visible to the whole team at once? | **Yes, everything is shared**: one common inbox. |

What changes:

- **G44 + G45** split the work in two places: the surface (definition, grill, spec) and a
  session whose working directory is a worktree under `projects/<name>/.worktrees/`. The
  surface's `.gitignore` covers `**/.worktrees/`, and any sync must skip these nested
  repositories.
- **G46 sets the priority of the first version**: the lifecycle commands. Automatic sync
  (watch), guards (size, secrets) and the project registry move to "useful, not indispensable":
  candidates for later versions, or for existing tools (Obsidian Git, gitleaks, a pre-commit
  hook).
- **G47**: no personal drafts; the inbox is shared and triaged by the priority decider (G16).

### Round 13

| # | Question | Answer |
| --- | --- | --- |
| G48 | If only the lifecycle is indispensable, is a Python CLI needed? | **CLI + bundled skill**: the CLI is the core, `aps` generates or installs the skill that teaches agents to use it (like `backlog instructions`). |
| G49 | What is the base repository of `.worktrees/<unique-name>/`? | **A hidden bare clone**, `projects/<name>/.repo.git` (git-ignored): one fetch, shared objects. |
| G50 | What does `aps take <slug>` do? | **Move to `03-requests/` + write `owner` and date**, commit and push at once (taking is a reservation). Not ticked: create the worktree, refuse if already taken, print the context. |
| G51 | How does `aps` know a CR landed? | **It is told**: `aps land <slug> --pr owner/repo#34`. No hosting access needed. |

What changes:

- **G48**: deliverables are the CLI and a skill (agent instructions generated from the CLI, so
  they never drift).
- **G49 + G50**: worktree creation is not part of `take`; the bare clone exists for agents that
  create worktrees (by hand or with a separate command, round 14).
- **G51** closes Q-E for the first version: no `gh` / `glab` dependency; `aps` stores what it is
  told.

### Round 14

| # | Question | Answer |
| --- | --- | --- |
| G52 | Alice and Bob both `take` the same idea 30 s apart. | **Not a problem, rare**; the conflict copy is enough to flag it. |
| G53 | Who creates the bare clones and worktrees under `projects/<name>/`? | **`aps workspace <slug>`.** |
| G54 | What does "split" an idea mean? | **New child ideas** that reference the parent. |
| G55 | Abandoned ideas? | Not answered: **the grill is going into too much CLI detail.** The user asked to stop the detailed study and see a complete end-to-end scenario instead: [research/end-to-end-scenario.md](research/end-to-end-scenario.md). |

### Round 15 — on the end-to-end scenario

| # | Question | Answer |
| --- | --- | --- |
| G56 | Agents analyse inbox ideas before triage? | **Yes, on demand** (the PO or a developer asks for one idea). |
| G57 | Is "only the PO accepts or rejects" enforced by the tool? | **Team convention**; the git log shows who decided. |
| G58 | A light grill before triage? | **No: the grill happens after `take` only.** The PO decides on the intent and the analysis. |
| G59 | The coding session writes reports into the surface, outside its own repository. | **Acceptable: direct write** by relative path; `save` / watch commits in the surface. |

The scenario's open points 1–3 and 5 are closed by these answers; point 4 (spec handoff) stays
open (G13).

### Round 16 — adoption and success

| # | Question | Answer |
| --- | --- | --- |
| G60 | First real user and project? | **The user alone, on their DevTools projects.** |
| G61 | Relation between `aps` and the Studio? | **Independent**: the Studio edits Markdown, `aps` does not know it. |
| G62 | Success criteria of v1? | **Migration done** (the Studio's `.agents/changes/` imported into a surface, gone from the code repository), **zero manual moves** (agents never move a folder by hand, no broken link), **two developers in parallel** (two people or two machines on one surface for a week, nothing lost). |
| G63 | If the team adopts Jira or Linear with an MCP server, is the surface useless? | **No, complementary**: the tracker keeps the ticket and the official priority, the surface keeps the rich definition; a link between both will be needed. |

### Round 17 — after the out-of-project comparison

Comparison: [research/prior-art.md](research/prior-art.md), section "Update after the model
inversion".

| # | Question | Answer |
| --- | --- | --- |
| G64 | Vibe Kanban already covers execution; should `aps workspace` redo it? | Counter-question: does Vibe Kanban do the grill, with prototypes? For the user, the surface must be **a Markdown viewing surface, to stay as flexible as possible**. |
| G65 | Would a template repository (template, skill, a few scripts) be enough for v1, with a CLI later? | **Template first.** |

What changes:

- **G64**: the product's identity is the **Markdown definition surface** (grill, spec,
  prototypes as files). Tools such as Vibe Kanban are execution tools with their state in an
  app; at most they consume a CR folder, they do not replace it.
- **G65 revises G48** (CLI + bundled skill) on sequencing: v1 is a **template repository** (the
  layout, `aps.toml`, the idea-folder template, a skill describing the lifecycle, and a few
  scripts for the moves that agents get wrong). The CLI is extracted later, from what actually
  breaks. To reconcile with G62 ("zero manual moves"): the scripts must cover folder moves and
  link rewriting from the start.

### Round 18 — v1 content

| # | Question | Answer |
| --- | --- | --- |
| G66 | Which scripts must exist in the v1 template? | **All four**: `move` (+ link rewriting), `new` (capture, slug uniqueness), `workspace` (bare clone + worktree), `save` / `sync` (conventional commit, rebase, push, conflict copy). |
| G67 | What does this `agentic-planning-surface` repository become? | **The user's first surface** (dogfooding, for their DevTools projects); the template is extracted later. |
| G68 | Consolidate now into `03-change-spec.md`? | **Yes, now.** See [03-change-spec.md](03-change-spec.md). |

### Round 19 — open questions of the spec

| # | Question | Answer |
| --- | --- | --- |
| G69 | Abandoned ideas? | **A trash folder** (`05-trash/`, numbered like the other state folders). |
| G70 | Name of the CLI? | **Decided later**, when the tool is extracted; `aps` is a working name. Revises A4. |
| G71 | Keep `NNN` in archived folder names? | **Yes, keep it.** Taken at landing, in landing order (Q-A option b). |

### Round 20

| # | Question | Answer |
| --- | --- | --- |
| G72 | Mapping of the Studio's folders into the surface? | **As proposed**: backlog keeps priorities; in-progress CRs drop `NNN`; archives keep `NNN`; orchestration files and locks not imported; heavy files dropped. See spec §13. |
| G73 | Where does this need-definition folder go? | **`projects/agentic-planning-surface/03-requests/need-definition/`** (the repository plans itself; typo fixed). |
| G74 | Next step? | **Devil's advocate on the spec**, section by section. |

### Round 21 — devil's advocate on spec §1–§3

| # | Question | Answer |
| --- | --- | --- |
| G75 | Surface as workspace means two VS Code windows and two sessions. | **Users create a multi-root workspace themselves**; the surface does not generate one. |
| G76 | A hidden bare clone duplicates the developer's own clone. | **Accepted: isolation.** Agents get their own clean, reproducible clone. |
| G77 | `take` moves a folder while another user edits it at the old path. | **The script repairs it**: `sync` detects a slug present in two state folders, moves the files into the most advanced one (conflict copy if needed) and reports it. |
| G78 | Idea coming from Jira: which one is the source of truth? | **The surface.** Jira is only an input; it is updated by hand if needed. |

### Round 22 — devil's advocate on spec §4–§6

| # | Question | Answer |
| --- | --- | --- |
| G79 | State is both in the path and in the front matter: two sources that will diverge. | **One single YAML file for the metadata** of an idea. |
| G80 | The PO accepts on a thin intent; the grill reveals the idea is huge or useless. | **Give it back to the backlog** (`03-requests` → `02-backlog`) with what the grill learned; the PO re-prioritises. |
| G81 | Debounced commits push half-written states that others see. | **Not a problem: it is a journal.** |
| G82 | Who starts `sync` when nobody thinks of it? | **The skill**: the agent runs `sync` at the start and end of each session, and the watch runs during the session. |

What changes:

- **G79**: metadata leaves the front matter of `01-intent.md` and goes to one `idea.yml` per
  folder (slug, projects, author, dates, owner, links, reason). The state and priority stay in
  the path only (G18); `idea.yml` does not repeat them. Assumption to confirm.
- **G80**: "give back" is a fifth lifecycle move, done by the owner; `owner` is cleared.

### Round 23 — devil's advocate on spec §7–§8

| # | Question | Answer |
| --- | --- | --- |
| G83 | Scripts copied into each surface will diverge. | **They become an installable executable**: a Python tool (`uv tool install`) or a Rust app. |
| G84 | Which agents must the skill support? | **`.agents/skills/`** (agent-neutral location). |
| G85 | Which links does `move` rewrite? | **Markdown links only** (`[text](path)`, `![](path)`). |
| G86 | How to check "two developers in parallel" while the user is alone? | **Two machines of the user.** |

What changes:

- **G83**: the template-first v1 is a short phase; the scripts are written so they can be lifted
  into one installable tool. Implementation language is open again: Python or Rust (intent §4.6
  said Python).
- **G85**: links inside `idea.yml` and in prototype HTML/SVG are not rewritten, so `idea.yml`
  refers to other ideas **by slug**, never by path; prototypes should only use paths inside
  their own folder.

### Round 24 — devil's advocate on spec §9–§10

| # | Question | Answer |
| --- | --- | --- |
| G87 | Size guard in v1, since history is never rewritten (G27)? | **Yes, minimal**: `save` and the watch refuse files above a size limit and blocked types, and report them. |
| G88 | Will this first surface be public on GitHub? | **Public.** |
| G89 | Next step? | **Commit the current state** of the need definition. |

What changes:

- **G87** moves a minimal size guard from "later" into v1.
- **G88** moves a minimal sensitive-content check into v1: at import and before each push
  (machine paths, e-mail addresses, tokens, names listed in the config). This need-definition
  folder is checked before its first commit.
