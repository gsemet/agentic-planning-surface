# End-to-end scenario

Captured 2026-10-23, after grill round 14 in [02-user-answers.md](../02-user-answers.md). It walks
one idea from capture to archive in the inverted model (G40). Command names are illustrative, to
make the flow concrete; they are not a CLI design.

## Cast and layout

- Team **acme**, two code repositories: `acme/studio` (GitHub) and `acme/okf-schema` (GitLab).
- **Camille** is the PO: decides priority, accepts or rejects ideas.
- **Alice** and **Bob** are developers; each drives their own agents.
- One planning repository, `acme-planning`, cloned by everyone:

```text
acme-planning/
├── aps.toml                     ← projects registry: name → remote URL; visibility; policy
├── _shared/                     ← cross-project ideas, same lifecycle folders
├── projects/
│   ├── studio/
│   │   ├── project.md           ← what the project is, remote, conventions
│   │   ├── 01-inbox/            ← captured, not triaged
│   │   ├── 02-backlog/P1|P2|P3/ ← accepted by the PO, prioritised
│   │   ├── 03-requests/         ← taken by one developer
│   │   ├── 04-archives/         ← landed, rejected, abandoned
│   │   ├── .repo.git/           ← hidden bare clone (git-ignored)
│   │   └── .worktrees/          ← code checkouts for agents (git-ignored)
│   └── okf-schema/ ...
└── .gitignore                   ← **/.repo.git, **/.worktrees
```

## Step 0 — Set up (once per team, once per machine)

- Camille creates the surface and registers the projects:
  `aps init`, `aps project add studio https://github.com/acme/studio.git`,
  `aps project add okf-schema https://gitlab.com/acme/okf-schema.git`.
- Alice joins: `git clone .../acme-planning && aps setup`. `setup` installs the agent skill and
  the git hooks. Nothing is cloned yet; code checkouts are created on demand.

## Step 1 — Capture

- Anyone adds an idea, from a chat, a bug, or a Jira ticket:
  `aps capture studio mermaid-error-dedup "Mermaid errors are shown twice"`.
- Result: `projects/studio/01-inbox/mermaid-error-dedup/` with `idea.yml` (slug, project,
  author, date; the state is the folder, G79) and `01-intent.md`, plus `intake/` when the source
  is an external ticket.
  Committed and pushed.

## Step 2 — Analyse the incoming ideas (agent)

- An agent is launched in `projects/studio/`, with the task "analyse the inbox".
- It needs the code, reproducibly: `aps workspace studio --ref main --name inbox-analysis`.
  This creates the bare clone if missing, fetches, and checks out a **read-only worktree at a
  known commit** in `.worktrees/inbox-analysis/`. The commit SHA is printed, so the analysis can
  quote it.
- For each inbox idea, the agent reads the code and adds what the PO needs to decide: affected
  areas, rough size, risks, duplicates of existing ideas, a recommendation. It writes them into
  the idea folder (`research/analysis.md`). It does not move anything.

## Step 3 — Triage (PO)

- Camille opens the inbox (in the Studio, on GitHub, or with `aps list studio --state inbox`)
  and reads the analyses.
- She decides, one command per idea:
  - `aps accept mermaid-error-dedup --priority P1` → `02-backlog/P1/mermaid-error-dedup/`;
  - `aps reject paste-as-image --reason "covered by 036"` → `04-archives/`, state `rejected`;
  - `aps split big-refactor parser-cleanup api-rename` → two child ideas in the inbox, each
    linking to its parent; the parent is archived as `split`.
- Every move rewrites the internal links and is committed with a readable message, so the log
  shows the PO's decisions.

## Step 4 — Take (one developer)

- Alice picks the top P1: `aps take mermaid-error-dedup` → `03-requests/mermaid-error-dedup/`,
  `owner: alice`, date. Pushed at once: the team sees the idea is taken.

## Step 5 — Full grill and spec (Alice + her agent, in the surface)

- Alice's agent works in the request folder: grills Alice, writes `02-user-answers.md`, then
  `03-change-spec.md`, with mock-ups in `prototypes/`. It reads the code through a workspace if
  needed.
- Alice can edit the same files in the Studio; changes are saved and pushed regularly.

## Step 6 — Implementation (Alice's coding session, in the code)

- `aps workspace mermaid-error-dedup` creates `projects/studio/.worktrees/mermaid-error-dedup/`
  on a new branch from `origin/main`, and prints how to start the coding session there, with the
  path of the spec.
- Alice starts the coding session in that worktree, so it loads the studio repository's own
  `CLAUDE.md` / `AGENTS.md`, skills and hooks (G45). The coding workflow is free: direct,
  spec-kit, OpenSpec. Its reports and reviews are written back into the request folder.

## Step 7 — PR and landing

- Alice opens the PR on GitHub, then records it: `aps link mermaid-error-dedup acme/studio#34`.
- After the merge: `aps land mermaid-error-dedup` → `04-archives/mermaid-error-dedup/`, state
  `landed`, PR reference kept. `aps workspace remove mermaid-error-dedup` deletes the worktree.

## Step 8 — Team view

- The generated view (Pages, light CI, G43) shows each project as columns: inbox, backlog by
  priority, requests by owner, recently landed. Camille follows the team from there.

## Cross-project variant

- An idea touching studio and okf-schema lives in `_shared/` and lists both projects. When taken,
  `aps workspace <slug> --project studio` and `--project okf-schema` give one worktree per
  repository, and the request records two PRs.

## Points this scenario makes visible

Answered in round 15 (G56–G59): 1 on demand, 2 convention, 3 after take only, 5 direct write.

1. **Analysis without being taken** (step 2): agents enrich inbox ideas before triage. Is that
   wanted, and is the analysis worktree shared by all ideas or one per idea?
2. **PO-only decisions** (step 3): is `accept` / `reject` restricted to the PO by the tool, or by
   team convention only?
3. **Grill before or after take**: here the full grill happens after `take` (step 5); a light
   grill may be needed before triage so the PO can decide.
4. **The spec lives in the surface**, the code in the worktree: the coding session reads it by
   path. The handoff to spec-kit / OpenSpec is still open (G13).
5. **Back-flow**: the coding session writes reports into the surface, which is outside its own
   repository. Is that acceptable, or does it write in its worktree and `aps` collects at landing?
