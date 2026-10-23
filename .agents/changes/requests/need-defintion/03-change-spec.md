# Change spec — agentic planning surface (v1)

Status: consolidated 2026-10-23 from [01-intent.md](01-intent.md) and the grill in
[02-user-answers.md](02-user-answers.md) (decisions `Gnn`). Where this file and the intent
disagree, **this file wins**; the superseded parts of the intent are listed at the end.
Research: [research/prior-art.md](research/prior-art.md),
[research/end-to-end-scenario.md](research/end-to-end-scenario.md).

## 1. What it is

A **planning surface**: one git repository of rich Markdown that sits **above** N code
repositories (GitHub or GitLab) and is shared by N users and their agents (G40). Each idea is a
folder that matures from capture to archive: intent, grill, spec, prototypes, research (G10, G13).
Humans view and edit it in any editor, on the hosting web UI, or in a generated view; agents use
their file tools (G20). It is complementary to a ticket tracker (G63); for an idea that comes from
one, the **surface is the source of truth** and the tracker is only an input (G78).

Why not in the code repository: planning on the main branch triggers heavy pipelines and pollutes
the code history; a remote tracker is too far from the agents, which need local Markdown (A1).

Prior art: the shape is an emerging pattern ("repo-of-repos"), but no tool found implements a
Markdown folder-per-idea lifecycle with PO triage and multi-user sync (prior-art, update).

## 2. Model

- **The surface is the workspace.** A developer and their main agent session work in the
  surface. Code repositories are checked out on demand under the surface (G40, G44).
- **Multi-project and multi-user by default.** One surface per team or product (G25); one code
  repository belongs to one surface only (G35).
- **Coding happens in a separate session** whose working directory is a code worktree, so it
  loads that repository's own `CLAUDE.md` / `AGENTS.md`, skills and hooks (G45). It writes its
  reports back into the idea folder by relative path (G59).
- Working in both places at once is left to the user (for example a multi-root VS Code
  workspace of the surface and a worktree); the surface does not generate one (G75).
- Agents always use the surface's own bare clone, never the developer's personal clones:
  isolation over disk space (G76).
- **Single-project mode** (optional, later): sparse checkout of one project's folder into a host
  repository's `.agents/changes/` (G40, G33).

## 3. Layout

```text
<surface>/
├── aps.toml                  ← projects registry (name → remote URL), visibility, policy
├── _shared/                  ← cross-project ideas, same lifecycle folders (G34)
├── projects/
│   └── <project>/
│       ├── project.md        ← what the project is, remote, conventions
│       ├── 01-inbox/         ← captured, not triaged
│       ├── 02-backlog/
│       │   ├── P1/
│       │   ├── P2/
│       │   └── P3/
│       ├── 03-requests/      ← taken by one developer
│       ├── 04-archives/      ← landed (`NNN-<slug>`), rejected, split
│       ├── 05-trash/         ← abandoned ideas (G69)
│       ├── .repo.git/        ← hidden bare clone (git-ignored) (G49)
│       └── .worktrees/       ← code worktrees, one per use (git-ignored) (G44)
└── .gitignore                ← **/.repo.git, **/.worktrees
```

- State and priority are **encoded in the path** (G18, G24); moving a folder is the transition.
- An idea's ID is its **slug**, unique across all state folders of the surface (G19).
- On landing, the archived folder is renamed `NNN-<slug>`: `NNN` is the next free number of the
  project, in landing order (G71). Landing is a single, serial event, so numbers are taken at
  that moment only, never at capture or take; a collision between two landings shows up on push
  and is fixed by taking the next number.

## 4. Idea folder

```text
<slug>/
├── idea.yml             ← required; the only metadata: slug, projects, author, created, owner,
│                          taken, links (PRs as owner/repo#n or group/project!n), reason (G79)
├── 01-intent.md         ← required; plain Markdown, no front matter
├── 02-user-answers.md   ← the grill: questions, answers, what changes
├── 03-change-spec.md    ← the precise spec handed to the coding session
├── prototypes/          ← optional: mock-ups, HTML, diagrams (G14)
├── intake/              ← optional: source material (e.g. a Jira ticket) (G22)
└── research/            ← optional: prior art, analyses (G28)
```

State and priority are read from the path only; `idea.yml` never repeats them (G18, G79).
More optional sub-folders may be added later. Markdown must render on GitHub, GitLab and in
plain editors, without editor-specific syntax (G20).

## 5. Lifecycle and roles

| Step | Who | Effect |
| --- | --- | --- |
| Capture | anyone (human, agent, intake) | new folder in `01-inbox/` (G47: visible to all) |
| Analyse | an agent, **on demand** | `research/analysis.md` in the idea; nothing moves (G56) |
| Accept + prioritise | the PO, **by convention** | `01-inbox/` → `02-backlog/Pn/` (G16, G57) |
| Reject | the PO | → `04-archives/`, reason recorded |
| Split | the PO or a developer | new child ideas referencing the parent; parent archived (G54) |
| Take | one developer | → `03-requests/`, `owner` + date, pushed at once (G50) |
| Grill + spec | the owner and their agent | `02-user-answers.md`, `03-change-spec.md`, prototypes (G58) |
| Implement | owner's coding session in a worktree | free workflow: direct, spec-kit, OpenSpec (G45) |
| Give back | owner | `03-requests/` → `02-backlog/Pn/`, owner cleared, learnings kept (G80) |
| Link PR | owner | PR reference written in `idea.yml` |
| Land | owner, **told**, no hosting access (G51) | → `04-archives/NNN-<slug>/`, state `landed`; worktree removed |
| Abandon | the PO or the owner | → `05-trash/`, reason recorded (G69) |

- The grill happens **after take only** (G58). One idea = one developer (G7); a double take is
  rare and surfaces as a conflict copy (G52).
- Every move rewrites the **internal Markdown links** (`[text](path)`, `![](path)`) into and out
  of the folder; external links may break (G21, G85). `idea.yml` refers to other ideas by slug,
  never by path, and prototypes only use paths inside their own folder.
- Execution control (rounds, reviewers, round limits, stale owners) is **out of scope** (G31);
  only each CR's state is versioned, not runtime files (G30).

## 6. Sync

- Every change is a commit with a readable, conventional message, so the log reads as a journal
  of decisions; half-written intermediate states are acceptable in it (G81).
- The skill tells agents to run `sync` at the start and end of each session and to keep the
  watch running during it (G82).
- Commits are debounced, Obsidian-Git style: commit after **30 s** of quiet, push every
  **2 min** (G32, G37). Pull is regular; open editors reload changed files (G41).
- On a rebase conflict: keep the remote version, write ours to `<file>.conflict-<user>.md`, push,
  report; nothing blocks, nothing is lost (G38). Offline work is normal; pending commits are
  shown and never dropped (G39).
- Writers in one working copy commit only their own paths; a busy `index.lock` is retried, never
  forced (intent 4.2).
- A slug found in two state folders (a move raced with an edit at the old path) is repaired by
  `sync`: files go to the most advanced state, with a conflict copy if needed, and it is
  reported (G77).
- History is **never rewritten**; the size policy prevents growth before commit (G27).

## 7. v1 deliverables — template first (G65, G66)

v1 is **not** a CLI. It is a surface with:

1. The layout above, `aps.toml`, the idea-folder template, `.gitignore`.
2. A **skill** in `.agents/skills/` (agent-neutral, G84) that teaches agents the layout, the
   lifecycle, the roles and the commit convention, and tells them to use the scripts for every
   transition.
3. Four **scripts** (Python for v1, runnable with `uv run`, non-interactive, `--json` output,
   clear exit codes):
   - `new` — capture an idea from the template; refuse a slug already used anywhere;
   - `move` — move an idea between state folders and rewrite internal links; `accept`, `reject`,
     `take`, `land`, `split` are thin wrappers or documented uses of it;
   - `workspace` — create the project's bare clone if needed and a worktree (read-only at a known
     commit, or on a new branch from `origin/main`); remove it;
   - `save` / `sync` — refuse files above a size limit (default 5 MB) and blocked types
     (packaged builds, videos, traces, archives), and content flagged by a minimal sensitive check
     (tokens, e-mail addresses, machine paths, names listed in the config), since this first
     surface is public (G87, G88); then commit with the convention, `pull --rebase`, push, conflict copy; a watch
     mode with the debounce of section 6.

The scripts are then lifted into **one installable executable** (a Python tool installed with
`uv tool install`, or a Rust app; G48, G83), so surfaces never carry diverging copies. It is
extracted from what actually breaks.
Its name is decided then (G70); `aps` and `aps.toml` in this file are working names.

**This repository becomes the user's first surface** (G67), for their DevTools projects; the
reusable template is extracted from it once it works.

## 8. Success criteria (G62)

1. **Migration done**: the Studio project's `.agents/changes/` is imported into this surface and
   no longer lives in the code repository.
2. **Zero manual moves**: agents never move an idea folder by hand; no broken internal link.
3. **Two developers in parallel**: two people or two machines use one surface for a week without
   losing a change; first checked on two of the user's machines (G86).

## 9. Later, not v1

- The CLI; single-project mode; generated view on Pages with a publish-only CI (G43).
- Full guards beyond the v1 minimum: per-archive size policy, `visibility: public|private`
  driving the strength of the check (G42), a pre-commit hook for raw `git` commits (G27).
- Spec handoff to spec-kit / OpenSpec (G13). Link with a ticket tracker (G63).

## 10. Out of scope

- Driving agents (starting sessions, scheduling), CI watching, reading PR/CI state (G31, G51).
- Merging host pull requests or acting on the code repositories' branches beyond creating
  worktrees.
- Integration with the user's Studio editor: the two stay independent (G61).

## 11. Superseded parts of the intent

- §3 "a dedicated Python CLI" as the first deliverable → template + skill + scripts first (G65).
- §4.1 "checked out into the host's planning folder", "one planning repository per host" →
  surface above N repositories, host checkouts under the surface (G25, G40).
- §4.1 "no CI" → a publish-only CI is accepted, later (G43).
- §4.3 machine-readable `STATE.md` header, orchestration status, round limits, stale owners →
  out of scope (G31); `NNN` taken at landing only, slug IDs before (G19, G71).
- §6 open questions 1, 2, 3, 6 → answered (G25, G40, G32, G51); 4 → one `idea.yml` per
  idea, no `STATE.md` header (G79); 5 → later (guards); 7 → later (G70).

## 12. Open questions

1. Who commits a human edit when no watch runs (G17)? v1 answer: the `save` / watch script;
   to confirm in use.

## 13. Migration of the Studio project (G72)

| Studio `.agents/changes/` | Surface `projects/studio/` |
| --- | --- |
| `backlog/P1\|P2\|P3/<slug>/` | `02-backlog/P1\|P2\|P3/<slug>/` |
| `backlog/INDEX.md` | regenerated; free-text decisions move to `project.md` |
| `requests/NNN-<slug>/` (in progress) | `03-requests/<slug>/`; `NNN` dropped, taken again at landing |
| `archives/NNN-<slug>/` | `04-archives/NNN-<slug>/`, `NNN` kept |
| `requests/ORCHESTRATOR*.md`, `*.lock` | not imported (local runtime, G30) |
| heavy files (packaged builds, videos, traces) | dropped before the first commit |

This need-definition folder moves to
`projects/agentic-planning-surface/03-requests/need-definition/` (typo fixed) when this
repository becomes a surface (G73).
