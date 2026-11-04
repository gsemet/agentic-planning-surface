# Change spec — agentic planning surface (v1)

Status: rewritten 2026-10-23 on the user's target organisation (round 25) and its gaps (round 26),
updated 2026-10-25 (rounds 31–32), in [02-user-answers.md](02-user-answers.md); decisions are
referenced as `Gnn`. This file wins over [01-intent.md](01-intent.md) and over earlier versions of
itself. Journey:
[research/user-journey.md](research/user-journey.md). Prior art:
[research/prior-art.md](research/prior-art.md).


## 1. What it is

A team's **planning surface**: one git repository of Markdown, above the team's code projects
(GitHub or GitLab), shared by every team member and their agents (G40, G25). It is the team's
common base for thinking about ideas before they become code. People read it in VS Code, in the
Markdown Studio, or on the hosting web UI (G20); agents use their file tools.

It is complementary to a ticket tracker: for an idea that comes from one, the surface is the
source of truth (G63, G78).

## 2. Journey (summary)

1. A newcomer clones the surface; the agent loads `AGENTS.md`, which points to the skills.
2. "I want to work on AAA": the skill presents AAA's inbox and backlog.
3. "Here is an idea: YYYY": the agent creates the idea in the inbox (G99).
4. The PO accepts it into the backlog (small team: the developer is their own PO).
5. Anyone runs a **product grill** or builds prototypes on it.
6. The PO accepts it as a **CR** by editing `idea.yml`; the git commit records who did it.
7. A builder volunteers; their agent moves the idea to `03-requests/`, creates a dedicated
   checkout of AAA, and starts a **technical grill** in a separate session there.
8. The builder's workflow (native, spec-kit, OpenSpec, ...) writes the spec, usually in AAA, and
   opens the PR on AAA.
9. After the merge, the builder says so; the CR is archived in the surface.

## 3. Layout

```text
<surface>/
├── AGENTS.md                 ← entry point: which skills to use, the rules below
├── .agents/skills/           ← the surface's skills (G84)
├── aps.toml                  ← projects registry (name → remote URL), policy
├── scripts/                  ← the v1 scripts (section 8)
├── _shared/changes/          ← cross-project ideas, same state folders (G34)
└── projects/
    └── <AAA>/
        ├── project.md        ← what AAA is, its remote, its closed decisions
        ├── changes/          ← the idea lifecycle (G115)
        │   ├── 01-inbox/         ← captured, not yet accepted
        │   ├── 02-backlog/P1..P4/ ← accepted by the PO; product grill and prototypes (G111)
        │   ├── 03-requests/      ← accepted as CR and taken by a builder; `ORCHESTRATOR.md`
        │   ├── 04-archives/      ← landed (`NNN-<slug>`) and rejected
        │   └── 05-trash/         ← abandoned
        ├── <other>/          ← room for other planning material: architecture, roadmap… (G115)
        ├── .repo/            ← project code checkout (out-of-tree case)
        └── .worktrees/       ← builders' checkouts of AAA, git-ignored (G96)
```

State paths below (`01-inbox/`, `02-backlog/Pn/`…) are relative to `projects/<p>/changes/`.

`aps.toml` and `aps` are working names; the tool's name is decided later (G70).

## 4. Change Request folder

```text
<slug>/
├── idea.yml             ← metadata (below)
├── 01-intent.md         ← the idea, plain Markdown
├── 02-user-answers.md   ← grills: product grill first, then the technical grill
├── 03-change-spec.md    ← copy of the final spec, added at archive time (G95)
├── STATE.md             ← execution state, from step 1 Pick on (section 6b)
├── task.md, rules.md    ← the builder's brief (step 4)
├── pr-body.md           ← draft PR description, reviewed before the PR opens (G113)
├── reports/, reviews/   ← per round, written by the builder's session
├── prototypes/          ← mock-ups, HTML, diagrams (G14)
├── intake/              ← source material, e.g. a ticket (G22)
└── research/            ← analyses, prior art (G28)
```

```yaml
slug: mermaid-error-dedup
projects: [AAA]
status: idea          # idea | accepted (set by the PO, G90)
builder: null         # set by the builder when they start (G91)
links: []             # PR and spec in the target project, as permalinks (G95)
```

- The **folder** gives the big stage and the priority (G18, G24); `idea.yml` gives what the
  folder does not: CR acceptance and builder (G90). Who did what comes from the git log, so
  there is no author or date field to maintain.
- The slug is the ID, unique across the surface (G19). `NNN` is added at archive time, in landing
  order (G71).
- Other ideas are referenced by slug, never by path (G85).

## 5. Roles and transitions

| Transition                | Who                                           | How                                                                                  |
| ------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------ |
| Capture                   | anyone, through the agent                     | new folder in `01-inbox/`, always (G99)                                              |
| Accept the idea           | the PO                                        | move to `02-backlog/Pn/`, P1 (first) to P4 (someday) (G111)                          |
| Reject / abandon          | the PO                                        | move to `04-archives/` (rejected) or `05-trash/` (abandoned), with a reason          |
| Product grill, prototypes | anyone                                        | files in the idea folder, in the backlog                                             |
| Accept as CR              | the PO                                        | edit `idea.yml`: `status: accepted` (G90)                                            |
| Start building            | a builder volunteers                          | `builder: <name>`, move to `03-requests/`, create the checkout (G91)                 |
| Technical grill           | the builder, separate session in the checkout | appended to `02-user-answers.md` (G92)                                               |
| Spec, code, PR            | the builder's workflow                        | in the target project, not in the surface                                            |
| Archive                   | the builder, after the merge                  | links + spec copy, move to `04-archives/NNN-<slug>/`, remove the checkout (G95, G96) |
| Give back                 | the builder                                   | `builder: null`, move back to `02-backlog/Pn/` (G80)                                 |

- Roles are a team convention, not enforced by the tool (G57).
- Every move rewrites the internal Markdown links into and out of the folder (G21, G85).

## 6. The builder's session (G92, G45)

- The skill creates the dedicated checkout of AAA in `projects/AAA/.worktrees/<slug>/`, on a new
  branch from the default branch named `change-requests/<slug>` by default, or by the target
  project's own branch rule when it has one (G109, G110, G104). It then prints the command to open a
  **separate agent session** there, with the path of the CR folder.
- That session loads AAA's own `AGENTS.md`, skills and hooks. It reads the CR folder by path and
  writes its technical grill back into it.
- Sub-agents are not relied on to load another project's instructions.

## 6b. CR execution state (G100–G103)

From the moment a builder picks an accepted CR, its folder holds a `STATE.md`, written by the
builder's session and pushed by sync, so the whole team sees where every CR stands (G100; this
reverses G31). It follows the Studio PRD workflow, kept as is (G102):

```text
driver: <agent id | none> · updated: <ISO timestamp with zone>
status: <working | wait-ci | ready | blocked | landed> · step: <1–11 name> · round: <n>/<limit>
head: <sha> · PR: <owner/repo#n | —> · run: <id> <pass | fail | pending>
next: <next action> · question: <question for the user, or —>

- [ ] 1 Pick · [ ] 2 Grill · [ ] 3 Open · [ ] 4 Brief · [ ] 5 Code · [ ] 6 Review · [ ] 7 Commit
  · [ ] 8 PR · [ ] 9 CI green · [ ] 10 Notify · [ ] 11 Land
```

| Step               | In the surface                                                   |
| ------------------ | ---------------------------------------------------------------- |
| 1 Pick             | the builder volunteers (`builder:` in `idea.yml`)                |
| 2 Grill            | technical grill, separate session in the checkout (G92)          |
| 3 Open             | move to `03-requests/`, create the checkout                      |
| 4 Brief            | `task.md`, `rules.md`, the `STATE.md` header                     |
| 5 Code → 10 Notify | unchanged from the Studio workflow (rounds, review verdicts, CI) |
| 11 Land            | archive (section 5)                                              |

- Round limit 3 by default; after it without green CI, `status: blocked` with a question.
- `STATE.md` is separate from `idea.yml`: it changes often, `idea.yml` stays stable (G101).
- Captured from the Studio: [research/cr-states.md](research/cr-states.md).
- The workflow around these steps (roles, round limit, rebase rule, parallel mode, sub-agent
  rules, `report.md`) follows the Studio PRD workflow:
  [research/cr-workflow.md](research/cr-workflow.md).
- **Who drives**: for a single CR, the builder's session in the checkout does steps 2–10 and
  starts coder and reviewer itself (G105). Parallel mode runs **per project**: one orchestrator
  and one open-PR cap per target project (G106); its CR table
  `projects/<p>/changes/03-requests/ORCHESTRATOR.md` is generated from the `STATE.md` headers and
  committed (G107).
- Environment-specific rules (model escalation, one real-window test at a time, stacked PRs) are
  surface defaults, overridable per project in `project.md` (G108).
- **Project rules first** (G104, G114): commit messages, PR / MR title and description, branch
  names, gates and screenshots follow the target project's own rules (its constitution first,
  then `AGENTS.md`, `CONTRIBUTING.md`, PR / MR templates, commit-lint config, `git log` style).
  The surface provides only defaults: Conventional Commits, and an external-reader PR template
  with a "Deliverables" section (cr-workflow §2). The PR body is drafted in `pr-body.md` first (G113).

## 7. Sync (G82, G93, G94)

- Sync runs **during agent sessions only**: the skill starts it with the session and stops it at
  the end. Outside a session, changes wait for the next one.
- While it runs: commit and push within **30 s** of a change, pull about every **30 s**, so a
  change reaches every other running session within **1 min** (round 25; replaces G37).
- Commit messages follow one convention, so the log reads as a journal; who did what is the git
  author.
- On a conflict, sync first tries a line merge; when that fails, the **agent merges** the two
  versions and commits (G94). Nothing is dropped.
- Offline work is normal; pending commits are pushed on reconnect (G39).
- A **size guard** (default 5 MB, blocked types: packaged builds, videos, traces, archives) and a
  minimal **sensitive check** (tokens, e-mail addresses, machine paths, listed names) run before
  each push, since the first surface is public (G87, G88). History is never rewritten (G27).

## 8. v1 deliverables (G65, G66)

This repository becomes the user's first surface (G67). It contains:
1. `AGENTS.md` only: the supported agents read it directly, no pointer files (G98).
2. The skills in `.agents/skills/`: project tour (step 2), capture, PO triage and acceptance,
   product grill, start building (checkout + separate session), archive.
3. Four scripts (Python, `uv run`, non-interactive, `--json`): `new`, `move` (+ link rewriting),
   `workspace` (checkout create / remove), `sync` (guards, merge attempt, push / pull loop).
4. The migration of the Studio project's old planning folder (mapping kept from the previous
   version: backlog keeps priorities, in-progress CRs drop `NNN`, archives keep `NNN`,
   orchestration files and heavy files are not imported; G72). Since 2026-10-25 the Studio's
   local folders already use `01-inbox` … `05-trash` and P1–P4, so the move is nearly 1:1;
   `02-decisions.md` becomes `02-user-answers.md` (G112).

The scripts are later lifted into one installable tool (Python with `uv tool install`, or Rust;
G83).

## 9. Success criteria (G62)

1. The Studio's old planning folder is migrated and gone from the code repository.
2. Agents never move an idea folder by hand; no broken internal link.
3. Two of the user's machines work on the surface in parallel for a week without losing a change
   (G86).

## 10. Not in v1

- A sync that runs without an agent session (service, VS Code task, extension) (G93).
- Automatic merge detection with `gh` / `glab` (G51, G96).
- A generated view on Pages (G43); single-project mode (G40).
- Full guards (per-archive size policy, visibility levels, pre-commit hook for raw git).

## 11. Closed questions (round 27)

1. A PO who only browses in VS Code sees changes at their next agent session, or after a manual
   `git pull`: **accepted for v1** (G97).
2. Agent entry point: **`AGENTS.md`** **only** (G98).
3. Capture always goes to the inbox; **the PO accepts** it into the backlog (G99).
