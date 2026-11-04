# CR workflow

Captured 2026-10-23 from the Studio project's PRD workflow guideline and its live CR table
(`ORCHESTRATOR.md`), at the user's request: "determine the workflow to follow". Section 1 is what
the Studio does; section 2 is how the surface adopts it. States: [cr-states.md](cr-states.md).
Updated 2026-10-25: the guideline is now `change-requests-lifecycle.guidelines.md` and the
Studio's local folders use the surface's numbered layout (section 1, "Layout").

**Key constraint (G104)**: the surface works on code projects that may have their **own rules for
commits and pull requests**. The surface only provides a **default** (commit format, PR
description); the target project's rules always win.

## 1. The Studio workflow, in short

### Vocabulary

- **Inbox item**: new idea, bug or request not yet prioritised, `01-inbox/<slug>/`; new items
  always land here, triage moves them to the backlog.
- **Backlog item**: prioritised, not started, `02-backlog/P1|P2|P3|P4/<slug>/` with `01-intent.md`
  and `02-decisions.md` (user decisions). P4 = someday.
- **CR**: one unit of delivered work = one branch = one PR with green CI, shipping code, tests
  (unit + e2e), documentation and screenshots for any visible change.
- **PRD folder**: `03-requests/NNN-<slug>/`, the only source of truth to resume a CR:
  `00-request.md` (intent + user decisions), `task.md` (brief: files, change, tests first, docs,
  gates), `rules.md` (hard rules for sub-agents), `STATE.md`, `reports/T1-r<n>.md`,
  `reviews/T1-r<n>.md`.
- **Archive**: `04-archives/NNN-<slug>/` = PRD folder + `report.md`.
- **Trash**: `05-trash/<slug>/`, abandoned idea kept for reference; only the user abandons.

### Layout (2026-10-25)

```text
.agents/changes/            ← still git-ignored local memory in the Studio
├── 01-inbox/<slug>/
├── 02-backlog/P1|P2|P3|P4/<slug>/
├── 03-requests/ORCHESTRATOR.md, ORCHESTRATOR-STATUS.md, NNN-<slug>/
├── 04-archives/NNN-<slug>/
└── 05-trash/<slug>/
```

This is the surface's per-project layout (spec section 3), with two differences: a fourth
priority, P4, and `NNN` taken at Open instead of at Land.

### Roles

| Role | Count | Does | Never |
| --- | --- | --- | --- |
| User | 1 | answers grills, grants extra rounds, merges PRs | — |
| Main session | 1 | talks to the user, steps 1–4, supervises the orchestrator | starts drivers, lands, edits a CR worktree |
| Orchestrator | 1 | starts and supervises drivers, watches merges, step 11, rebase requests | long commands, code, review, commit, merge |
| CR driver | 1 per CR | steps 5–10, starts coder and reviewer, watches its CI | code, review, touch another CR |
| Coder | 1 per round | changes the worktree, runs local gates, writes the report | commit, push, outlive its round |
| Reviewer | 1 per round | verifies the diff read-only, writes the verdict | edit files, outlive its round |

- Model escalation: the coder moves to a stronger model after the second `FIX-REQUIRED` or two CI
  failures with the same cause; the reviewer uses it when the blast radius is 2 or 3.
- **Never move a task up a level**: a failing child is restarted, never replaced by its parent.

### Lifecycle and rules

- 11 steps, Pick → Land, with owners and transitions: see [cr-states.md](cr-states.md).
- **Round limit**: 3 rounds per CR (review and CI failures together); then `status: blocked` with
  a question. Only the user grants more rounds.
- **Rebase rule**: when any PR merges, every open CR branch is rebased on `origin/main` and pushed
  with `--force-with-lease`; no merge commits.
- **Parallel mode**: one orchestrator, one driver per CR, cap on open PRs (default 4). The
  orchestrator ticks every 4–5 min, rebuilds a status file from the `STATE.md` headers, lands
  merged CRs, restarts stuck children (header older than 15 min), resumes crashed ones.
- **Responsiveness**: no agent blocks more than 5 min; CI is watched in slices of ≤ 5 min.
- **Stacked PRs** (GitHub): optional, proposed by the orchestrator, ordered by dependencies and
  risk; one stack driver owns all stacked branches.
- **CR table** (`03-requests/ORCHESTRATOR.md`): three sections, Active, **Backlog** (items of
  `02-backlog/P*/` not yet started: priority, item, title, file count) and Landed; it replaces the
  former `backlog/INDEX.md`. Every cell that names a file or a PR is a link (spec, `STATE.md`, PR).
- **Branch names** (2026-10-23, prefix fixed 2026-10-25): `change-requests/NNN-<slug>` (CR
  number with leading zeros + CR folder name, `NNN` taken at Open); the change type lives in
  commits and the PR title, not in the branch. Older branches keep their names. The prefix was
  first committed as `changes-requests/`; the fix to `change-requests/` is still uncommitted in
  the Studio, and its live CR table and stack brief still show the old spelling.
- **Constitution** (2026-10-24): `.agents/constitution.md` ranks above `AGENTS.md`, the
  guidelines and the skills; sub-agents read it first. In the Studio it holds the requirements
  rule (SwRS anchored to code with `@implements_req` / `@tests_req`, updated in the same task),
  the layer and file-size rules, and the test rules.
- **macOS**: while app-window tests may run locally, the orchestrator keeps the machine awake
  (`caffeinate -dimsu -t 21600`, restarted at a tick, stopped only if it started it).

### Rules about the code repository

- **Commits**: explicit paths only (never `git add -A`), the project's commit format
  (Conventional Commits in the Studio).
- **PR body for an external reader**: explain from the reader's side; no internal ids (CR
  numbers, backlog ids, rounds, agent roles, planning paths) in the text; internal references
  only in a last "Internal references" section; title = a Conventional Commit subject; body kept
  up to date with the scope; decisions taken without the user under "Autonomous decisions".
- **PR "Deliverables" section** (2026-10-24, renamed from "How it works" on 2026-10-25): right
  after Summary, what the reader gets, shown with one or more small visuals, each next to the
  sentences it supports: a Mermaid flowchart (≈ 10 nodes), a sequence diagram
  of one real flow, a before/after tree or table, or a 5–15 line code sketch; real names checked
  against the code. A one-line fix may skip it; a structural change never does.
- **Screenshots**: from the final e2e/visual run, light and dark; pushed as raw blobs to a
  `change-requests/NNN-<slug>-assets` side branch (formerly `pr-assets/<n>`) and linked by raw
  URL. Landing removes the CR branch and keeps the `-assets` branch.
- Everything written to the repository or the hosting service is in English.
- Shell: `\rm`, `\cp`, `\mv` to bypass interactive aliases; no command waits for input.

### Observed practice, beyond the guideline (2026-10-25)

- The live CR folders hold `01-intent.md`, a **`pr-body.md`** draft (reviewed before the PR is
  opened) and `reports/`; no `00-request.md`, `task.md`, `rules.md` or `STATE.md` yet (status
  shown as "briefed", a value not in the documented list).
- A stacked batch shares one **`STACK-BRIEF.md`** (coders) and one **`REVIEW-BRIEF.md`**
  (reviewers) in `03-requests/` instead of a `task.md` / `rules.md` per CR.
- The CR table is already **generated** by a script (`03-requests/refresh_orchestrator.py`), with
  hard-coded repository, paths and subjects; it still reads the pre-rename folders, so the table
  links point to `../backlog/` and `../archives/`.
- Step 11 still says "update `INDEX.md`", which no longer exists.

### Sub-agent rules (copied into `rules.md`)

- Work on the CR branch only; never commit, push, stash or switch branches.
- Read the project constitution first; it ranks above the briefing.
- No installs, no network unless the project allows it.
- Run only the gates listed in `task.md`, in the foreground; leave nothing running.
- Touch only the needed files; never change an assertion's intent; new tests must fail on the
  unchanged code.
- Report: files changed, tests and their failure before the change, changed assertions and why,
  gate results with counts, screenshot paths, open points.

### `report.md` (archive)

Status (done / partial, date, branch, PR, merge commit); Delivered (task, change, commit); Proof
of completion (tests, gate counts, CI run, screenshots); Open items.

## 2. How the surface adopts it

### What is kept as is

Roles, the 11 steps (G102), round limit, rebase rule, responsiveness, supervision rules,
sub-agent rules, `task.md` / `rules.md` / `reports/` / `reviews/` / `report.md`, the `STATE.md`
header (G100–G103).

### What changes because of the surface

| Studio | Surface |
| --- | --- |
| `.agents/changes/` git-ignored, "never link to it" | the surface is a public git repository; the CR folder can be linked (permalink) in "Internal references" |
| `03-requests/NNN-<slug>/`, `NNN` taken at Open | `projects/<p>/changes/03-requests/<slug>/`, `NNN` taken at Land (G71) |
| `00-request.md` | `01-intent.md` + `02-user-answers.md` (product then technical grill) |
| worktree `../<repo>-wt-NNN` | `projects/<p>/.worktrees/<slug>/` (G96) |
| main session (steps 1–4) + orchestrator + one driver per CR | product work in the surface; for a single CR, **the builder's session** in the checkout does steps 2–10 and starts coder and reviewer itself (G92, G105) |
| `ORCHESTRATOR.md` CR table, hand-maintained | `projects/<p>/changes/03-requests/ORCHESTRATOR.md`, **generated** from the `STATE.md` headers and the backlog folders, with the same Active / Backlog / Landed sections, and **committed** (G107) |
| `ORCHESTRATOR-STATUS.md`, locks | local runtime, not versioned (G30) |
| one project, one orchestrator | parallel mode **per project**: one orchestrator and one open-PR cap per target project (G106) |
| model escalation, one real-window test at a time, keeping a Mac awake, stacked PRs | **surface defaults**, overridable per project in `project.md` (G108) |

### Project rules first, surface defaults second (G104)

For every rule that touches the **code repository**, the builder's session looks for the target
project's own rule first, and uses the surface default only when none exists:

| Topic | Target project's rule, looked up in | Surface default |
| --- | --- | --- |
| All topics | the project constitution first (`.agents/constitution.md`, `CONSTITUTION.md`), then the files below | — |
| Commit message | `AGENTS.md`, `CONTRIBUTING.md`, commitlint / commitizen config, recent `git log` style | Conventional Commits (`type(scope): subject`), English, attribution trailer if the agent's harness requires one |
| PR / MR title | same | a Conventional Commit subject |
| PR / MR description | `.github/pull_request_template.md`, `.gitlab/merge_request_templates/`, `CONTRIBUTING.md` | the "external reader" template below |
| Branch name | `AGENTS.md`, `CONTRIBUTING.md` | `change-requests/<slug>`, no `NNN` (taken at landing, G71) (G109) |
| Gates (tests, lint) | `AGENTS.md`, CI config | none: the builder asks |
| Screenshots | `AGENTS.md`, `CONTRIBUTING.md` | GitHub: `<CR branch>-assets` side branch, kept after landing; GitLab: MR attachments |
| Merge strategy, rebase | branch protection, `CONTRIBUTING.md` | rebase on the default branch, `--force-with-lease`, no merge commits |

Default PR description (when the project has no template):

```markdown
## Summary

<what was wrong or missing, what this PR changes, what the reader will notice>

## Deliverables

<what the reader gets, with one or more small visuals (Mermaid flowchart or sequence,
before/after tree or table, code sketch), each next to the sentence it supports; may be skipped
for a one-line fix>

## Changes

- <change, from the reader's side>

## Tests

- <tests added (failed before, pass after), gates run, CI>

## Impacts

<visible changes, screenshots light/dark>

## Autonomous decisions

- <decision taken without the user, and why> (omit if none)

## Internal references

- Planning: <permalink to the CR folder in the surface>
```

The skill states the lookup order; it does not copy any project's rules into the surface.
