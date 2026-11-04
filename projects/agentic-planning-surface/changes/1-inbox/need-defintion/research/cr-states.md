# CR states

Captured 2026-10-23 from the Studio project's `STATE.md` of CR 048 and its PRD workflow guideline
(the `STATE.md` header section and the lifecycle table). Section 1 is what exists; section 2 is a
proposal to formalise it in the CR folders of this surface, to validate.

## 1. What exists today (Studio PRD workflow)

### Example: CR 048, `STATE.md`

```text
driver: cr048-driver · updated: 16:43
status: working · step: 5 Code · round: 1/3
head: 6347b9c · PR: — · run: —
next: coder r1 running (root cause undo + slash menu) · question: —

- [x] 1 Pick · [x] 2 Grill · [x] 3 Open (<worktree path>, `fix/local-undo-macos`) · [x] 4 Brief
  · [ ] 5 Code · [ ] 6 Review · [ ] 7 Commit · [ ] 8 PR · [ ] 9 CI green · [ ] 10 Notify · [ ] 11 Land
```

### Header fields

| Field | Values | Meaning |
| --- | --- | --- |
| `driver` | agent id, or `none` | lock: at most one live driver per CR |
| `updated` | `HH:MM` | last rewrite; used to detect a stuck child (> 15 min) |
| `status` | `working`, `wait-ci`, `ready`, `blocked`, `landed` | the CR's situation |
| `step` | `1`–`11` with its name | where the CR is in the lifecycle |
| `round` | `n/limit` (limit 3 by default) | coder passes, review and CI failures together |
| `head` | commit SHA | last commit of the CR branch |
| `PR` | `#n` or `—` | pull request on the code repository |
| `run` | run id + `pass` / `fail` / `pending` | last CI run |
| `next` | free text | next action |
| `question` | free text or `—` | question waiting for the user |

Observed values across the Studio's CR folders: `ready` (12), `working` (4), `wait-ci` (3),
`landed` (1), and once `done` (not in the documented list).

### Steps

| Step | Owner | Action |
| --- | --- | --- |
| 1 Pick | main session | propose the item: problem, file:line, fix, PR content |
| 2 Grill | main session | questions that change the result; answers in `00-request.md` |
| 3 Open | main session | create the PRD folder, move the backlog content, worktree + branch |
| 4 Brief | main session | `task.md`, `rules.md`, `STATE.md` header |
| 5 Code | coder | round n, local gates, `reports/T1-r<n>.md` |
| 6 Review | reviewer | `reviews/T1-r<n>.md`: `APPROVE` or `FIX-REQUIRED` |
| 7 Commit | driver | explicit paths only |
| 8 PR | driver | rebase, push, open the PR |
| 9 CI | driver | watch the checks |
| 10 Notify | driver | CI green → `status: ready` |
| 11 Land | orchestrator | after the user merges: `report.md`, move to archives, remove worktree |

### Transitions

```text
1 Pick → 2 Grill → 3 Open → 4 Brief → 5 Code ⇄ 6 Review → 7 Commit → 8 PR → 9 CI → 10 Notify → 11 Land
                                       ▲        │ FIX-REQUIRED (round n+1)
                                       └────────┘
                                       ▲                                 │ product/test failure (round n+1)
                                       └─────────────────────────────────┘
9 CI, infra failure        → re-run once, same round
round > limit, not green   → status: blocked + question (only the user grants more rounds)
any PR merged elsewhere    → rebase the open CR branches, back to 9 CI
```

`status` by step: `working` during 1–8 and after a failure; `wait-ci` during 9; `ready` at 10;
`blocked` when stuck on the round limit or a question; `landed` at 11.

## 2. Decision for this surface (round 28, G100–G103)

The proposal of a simplified YAML state in `idea.yml` was **not** kept. The user chose:

- **Full state** of a CR in progress is versioned in the surface: driver, step, round, branch, PR,
  CI, next action, question (G100; reverses G31).
- It lives in a **separate `STATE.md`** in the CR folder, rewritten often by the workflow, while
  `idea.yml` stays stable (G101).
- The **Studio's 11 steps** are kept as they are (G102).
- The **builder's session** writes it, by relative path, like its reports (G103, G59); sync pushes
  it.

How the 11 steps map onto the surface:

| Step | In the surface |
| --- | --- |
| 1 Pick | the builder volunteers on an accepted CR (`builder:` in `idea.yml`) |
| 2 Grill | the technical grill, in the separate session (G92) |
| 3 Open | move to `03-requests/`, checkout in `projects/<p>/.worktrees/<slug>/` |
| 4 Brief | `task.md`, `rules.md`, the `STATE.md` header |
| 5–10 | unchanged: Code, Review, Commit, PR, CI, Notify |
| 11 Land | archive: links + spec copy, move to `04-archives/NNN-<slug>/`, remove the checkout |

`STATE.md` keeps the Studio's four-line header and checklist. One change: `updated` is an ISO
timestamp with time zone (`2026-10-23T16:43+02:00`) instead of `HH:MM`, because several people
and machines read it across days (assumption, to confirm).
