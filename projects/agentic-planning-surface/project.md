# aps — agentic planning surface

The tool and template behind this surface: a team git repository of Markdown, above the team's
code projects, where ideas are captured, grilled and accepted before they become code. `aps` is a
working name; the final name is decided later (G70).

Need and design: [changes/01-inbox/need-defintion/](changes/01-inbox/need-defintion/03-change-spec.md).

## Repository

- Remote: [gsemet/agentic-planning-surface](https://github.com/gsemet/agentic-planning-surface)
  (GitHub, public).
- Default branch: `master`.
- **Self-hosted**: the code repository of this project is the surface itself. There is no hidden
  clone (`.repo.git`): builders' checkouts are worktrees of the surface's own repository.

  ```bash
  git worktree add -b change-requests/<slug> projects/aps/.worktrees/<slug> origin/master --no-track
  ```

  `projects/aps/.worktrees/` is git-ignored. A checkout of the surface contains `projects/aps/`
  too: the builder's session edits code in the checkout and planning files (grill, `STATE.md`,
  `pr-body.md`) in the main clone, by absolute path, so sync never sees two copies of a CR folder.

## Rules for changes

No `AGENTS.md`, `CONTRIBUTING.md` or PR template yet, so the surface defaults apply (G104):

| Topic | Rule |
| --- | --- |
| Branch | `change-requests/<slug>`, no `NNN` (G109, G110) |
| Commit | Conventional Commits, in English, explicit paths only; trailer `Assisted-by: Claude:<Model>` |
| PR | title = a Conventional Commit subject; body drafted in the CR folder's `pr-body.md` with the default external-reader template (Summary, Deliverables, Changes, Tests, Impacts, Autonomous decisions, Internal references) |
| Gates | none yet (no code); added here with the first script |
| Screenshots | none expected (CLI and Markdown) |

## Overrides of surface defaults (G108)

None.

## Closed decisions

The decisions G1–G115 in
[02-user-answers.md](changes/01-inbox/need-defintion/02-user-answers.md) hold until the need is
accepted; the decisions that still apply are summarised in the
[change spec](changes/01-inbox/need-defintion/03-change-spec.md).
