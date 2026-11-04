# 03 — Where judgment really happened (transcripts 2026-10-17 to 10-27)

Scope: main session `dd375646` plus its 1139 subagents, read-only. Session `c985a2ca` is excluded,
and so is `069f6dee`, which was APS design work and not the factory.
The factory window is 2026-10-22T16:00 to 10-27, covering about 115 CRs (024–148) and CR 135 with its 26 tasks.
Run state was read from `markdown-okf-schema-studio/.agents/changes/{03-requests,04-archives}`.
Lines marked *(inferred)* are my interpretation. Everything else is quoted or counted.

Scripts are in [scripts/](scripts/):
- `index_agents.py` builds the agent tree.
- `condense.py` produces condensed timelines for 190 orchestrator, driver and stack-driver agents.
- `handbacks.py` collects every SubagentHandback of those agents.
- `main_session.py`, `burden.py`, `catalog.py` and `agent_cost.py` handle classification and cost.

Prices follow §2 of `rapport-cout-orchestration.en.md`: Opus 4/5/8/0.20/20 and Sonnet 2/2.5/4/0.20/10 $/MTok, with synthetic messages excluded.

## Scale of what the orchestration layer did (since 10-22 16:00)

| Activity in orchestrator, driver and stack-driver agents | Count |
|---|---|
| Agent spawns | 820 |
| CI watch commands (`gh run watch` / `gh pr checks --watch` / poll loops) | 475 |
| `sleep` invocations (41 were blocked by the harness) | 561 |
| `gh run rerun` / `gh run cancel` | 54 / 25 |
| git rebase / force-with-lease push | 147 / 72 |
| Heavy-CI dispatches | 34 |
| Tool errors (`RESULT-ERR`) | 295 (174 non-zero exits, 100 tool_use_error, 56 missing files) |
| API deaths (403 ECONNRESET, auth, session limit) | 16 |
| Permission-classifier denials in orchestrator-type agents | 5 distinct reasons, about 7 events counting coder and reviewer |

Subagent cost by role since 10-22 16:00:

| Role | Cost |
|---|---|
| Orchestrators | $115.17 |
| CR drivers | $83.76 |
| Stack drivers | $23.34 |
| Task drivers | $7.93 |
| Conflict fixers (21 agents) | $3.22 |
| Integrator | $1.21 |
| **Orchestration layer total** | **about $234.6, which is 18% of $1272** |
| Coders | $530 |
| Reviewers | $185 |
| Other | $323 |

---

## Part A — Improvisation catalog

The "Rule?" column says whether the case can become a `crf` rule, needs an LLM, or should block.

| # | Category | Count | Evidence (file · ts · quote) | Outcome | Rule? |
|---|---|---|---|---|---|
| 1 | `just dev-ci` hang / infra re-runs beyond one | Oct 22–23 night: about 10 CRs needed 2–6 attempts; later 3 heavy runs hung in the untrusted suite and 051 hit stress ETIMEDOUT | night orchestrator a4ac0655 · 10-23T03:59 · "the `dev-ci` step hung for 20 to 60 minutes on nearly every PR, so every driver cancelled and re-ran it" — CR 035 driver · 10-23T00:17 · "it took four attempts… This goes past the single re-run you allowed, because each failure had a different cause" — 031 attempt 6, 036 five attempts | All merged. Fixed for good by CR 041 (cached .deb) and CR 044 | **Rule**: detect a step that has no output for N min, then cancel and re-run, up to K times per CR |
| 2 | Flaky test judged "unrelated" | 8–10 CRs; 4 recurring tests (linked-target watcher, "StRS-A link has a box", Tab timeout, toolbarReq under load) | CR 031 driver · handback · "Main itself fails CI often, so I judged both flaky" — CR 034 · round 3 · "failed 3 of 3 times… coder showed it also hit main" | Mostly merged as flaky. 034 fixed the watcher for real | **Rule** when the test is untouched by the diff and is red on base, or is on a known-flake list. Otherwise **LLM** |
| 3 | Rebase conflicts | Many over about 40 rebases with conflicts. Files: CHANGELOG (7), e2eGroups counts ("382+5=387"), requirements log and index, test registries. ID collisions renumbered: TABLE-003→007, BLOCK-002→003/004, visual v23-24→v25-26 | stack driver · "Keep both. A script to resolve CHANGELOG by dropping markers" | Resolved by 21 conflict-fixer agents ($3.22) and by drivers | **Rule** for most of them: union-merge append-only files, regenerate counts and indexes, allocate IDs at `crf open`. **LLM** for the few semantic ones (T11 mathRenderer, 051 extension.ts, 048) |
| 4 | Shared node_modules drift | 5 CRs (045, 056, 057, 131, 135-T1) | 131 · "the shared symlink would have changed other worktrees" — 135 T1 · 16:45 · coder patched the shared markdown-it-myst, then "the permission classifier denied the revert" | T1 blocked; the others worked around it | **Rule**: run a private `npm ci` when package*.json changes; mount the shared tree read-only |
| 5 | Tool and environment drift (stale okfreq, `--check-links`) | CRs 114–143, every CR 135 task; run 2 (125–131): 7/7 PRs red on static | stack 125–131 · `just requirements-update` denied "[Modify Shared Resources]", user authorized it at 11:59 — 132–134 fix `uvx --from okf-schema==0.13.0` | Drivers compared each failure against the base by judgment, CR by CR | **Rule**: run a baseline gate on the base branch at run start. If the base is red, stop the *run* once with one cause, not N CRs |
| 6 | Permission denials | About 7 events | 110 r2 · `reset --soft` and force push denied, fell back to a follow-up commit — CR 123 landing · worktree removal "[Irreversible Local Destruction]" — P1+P2 · branch delete and "[External System Writes]" — 135 T1/T15 reviewer · revert denied | Mostly worked around | **Rule** (as in the sketch): record and continue; never squash with `reset` (use `rebase --onto` fixup); do cleanup inside `crf land` |
| 7 | Locked screen and window-lock contention | Screen locked: 8 CRs (039, 040, 056, 058, 113, 115, 123, 124). Lock contention: 4 (132 held by 134, 127 lock vanished, 143 QA window opened while the lock was held, T17 waiting) | `WINDOW-TESTS.lock` content "T18 22:38"; drivers used heavy CI as proof instead | All proceeded via heavy CI | **Rule**: a lock queue in `crf`, plus `CGSSessionScreenIsLocked` detection that switches the required proof to heavy CI |
| 8 | Round limit exhausted | 5 CRs needed extra rounds (025 9/9, 041 4/6 granted, 113 r4, 115 r4, 123 r4–6); 6 more finished at exactly 3/3 | main session · 10-26 night · granted rounds 4 and 5 to 123 and started 115 rounds 2 and 4 on Opus | All merged in the end | **Blocked**, or **LLM conductor** with a delegated extra-round budget |
| 9 | Spec gaps decided autonomously | About 27 CRs with an "Autonomous decisions" section | 037 grid breakpoints 480/640/800 px; 046 glow at 600 ms instead of 100–200 ms; 038 lossy conversions refused | Merged and reported | **LLM** (coder or reviewer). Must not block |
| 10 | Questions with recommended answers | About 22 CRs | Typically "merge as is, follow-up CR" | Non-blocking | **LLM** writes them; `crf` collects them into a digest |
| 11 | Forge and stack surprises | About 5 stack-level events | 12 PRs `mergeStateStatus BLOCKED` from branch protection; PR #129 auto-marked merged on restack → new #130; base cycle #128↔#129 (caught by the main session at 02:59); a branch rename closed #88, #89, #92; `gh pr edit` cannot retarget inside a stack | Each repaired by an LLM, often the main session | **Rule** after the first occurrence (verify bases with `crf stack`, never rename). Until then: **blocked** |
| 12 | Cross-CR regression found by heavy CI at the stack top | 6 cases | #87 sender check broke host messages (reload-only failed 9/9, bisected with revert probes); PR #82 behaviour change → fix CR 104; 114×115 cell editor; 114 label vs realInput; 113 tableEmptyColumn; 123 editToolbarCover — main · 10-26T04:05 · "Le blocage n'est pas un problème de machine de CI : c'est une vraie régression" | Bisect with 3 parallel heavy runs, twice. Fix CR or round added | **Bisect = rule** (`crf` runs heavy CI on each stack prefix). **Attribution and the fix choice = LLM** |
| 13 | Evidence mismatch / not reproducible | About 9 CRs | Reopened by user feedback: 107, 109, 110, 112, 113; orchestrator accepted 115's mismatch on its own judgment; 121 not reproducible → blocked; 123 "before-shot matches user evidence: no"; 134's symptom did not reproduce | Mixed | **LLM** reviewer. A non-reproducible bug is a legitimate **block** |
| 14 | Dead or stalled children | 7 orchestrator TaskStops (Oct 22–23, frozen on foreground Agent calls); 1 API death took down 7 children (a21e1ec0, 10-27T18:08, 403 ECONNRESET); 2 rate-limit resumes; 3 drivers handed back before CI finished (044, 051, 053); P1 orchestrator handed back interim results 4× | main · 10-22 · "you have been blocked since 22:55 because your four driver Agent calls…" — restart after the API death came only at 19:14, when the user typed "contineu" (65 min idle) | Each needed the main session | **Rule**: a script loop has no LLM to freeze. `crf status` detects a dead coder; resume is mechanical |
| 15 | Process deviations | About 4 | Drivers coded or reviewed themselves (024, 113 round 4); BSD `sed -i`, zsh quoting, aliases (about 40 driver reasoning lines) | Worked | **Rule** (no driver role); shell helpers inside `crf` |
| 16 | Stale state files | 4 or more | STATE.md 113 says 2/3 and 115 says 1/3, but both ran 4 rounds; TASKS.md T17 still "pending 0/3"; ORCHESTRATOR-STATUS.md stale | Main session re-derived state from git or gh at high cost | **Rule**: `crf render` from the source of truth (gh, git, round files) |

### Blocked CRs under the sketch as written ("infra = one re-run, unknown = blocked")

| Period | Blocked (estimate) | Main cause |
|---|---|---|
| Oct 22–23 night (12 CRs) | about 8 | 1 on rounds (025), about 7 on the re-run budget (031, 034–039) |
| Oct 23 day | 1–2 | |
| P1+P2 stack | about 2 stack-level | forge surprises |
| P1 stack 107–124 | about 6 CRs (110, 113, 115, 121, 122, 123) plus about 2 stack-level | rounds, evidence, cross-CR regression, external dependency (122 waits for okf-schema 0.15.0) |
| Run 2 (125–131) | 7/7 | one environment cause |
| Run 3 / Run 4 (135) | 0–1 / 1–2 | node_modules, permission |
| **Total** | **about 20–25 of about 115 CRs (about 20%), plus about 5 stack-level blocks** | |

These blocks would cost about **2–5 user interruptions per run** if `crf` groups them by cause, and up to 8 on a bad night.
With the rules from rows 1–7, 14 and 16 *(inferred)*, the count drops to **about 6–8 blocks over the whole period, or 1–2 per run**.
Those remaining blocks are rounds, evidence mismatch, cross-CR regression and external dependencies.

---

## Part B — Main-session orchestration burden (dd375646, since 10-22 16:00)

The main session ran 1558 turns for **$128.47** (Opus) in this period.
Over the whole window (Oct 20–27) it ran 2383 turns for $197.9, which matches §4.6 of the cost report ($218 for Oct 19–26).
Turn categories come from the tools called in each turn.

| Category | Turns | Cost |
|---|---|---|
| orch-forge (gh pr/run/checks, heavy CI, bisect) | 279 | $35.53 |
| orch-state (reading STATE, TASKS, status, worktrees) | 216 | $20.04 |
| orch-relay (SendMessage, TaskStop) | 114 | $8.53 |
| orch-poll (sleep, waits) | 61 | $5.87 |
| orch-launch (Agent) | 38 | $3.41 |
| orch-script | 5 | $0.64 |
| **Orchestration total** | **713 (46%)** | **$74.0 (58%)** |
| work-tool (real work: edits, reads for the user) | 471 | $30.06 |
| text-only (talking to the user) | 342 | $22.12 |
| backlog | 27 | $1.76 |

Sub-split by activity:

| Activity | Turns | Cost |
|---|---|---|
| status-read | 127 | $17.50 |
| CI, heavy CI and bisect | 109 | $16.15 |
| relay or stop | 114 | $8.53 |
| land and cleanup | 42 | $2.75 |
| launch | 38 | $3.41 |
| merge or rebase done itself | 38 | $2.82 |
| open-CRs | 31 | $2.68 |
| other-orch | 209 | $19.88 |

The conservative core (status, CI, relay, land, launch, merge, open) is **about 504 turns and $54, or 42%**.

Episodes are grouped by what triggered them:

| Episode class | Episodes | Turns | Cost |
|---|---|---|---|
| user content, not orchestration | 106 | 459 | $32.34 |
| user content about orchestration | 64 | 389 | $29.91 |
| machine-triggered orchestration (notifications) | 43 | 190 | $25.39 |
| machine relay (agent message → forward) | 43 | 152 | $10.00 |
| user says "merged" | 39 | 227 | $16.94 |
| user status question | 22 | 90 | $6.03 |
| user says "continue" | 10 | 51 | $7.86 |

About **75% of main-session cost sits in orchestration-driven episodes**.

The session received these inputs over the window:

| Input | Count |
|---|---|
| Unique human prompts | 286 |
| Agent messages | 207 |
| Task notifications | 115 |
| Compactions | 17 (12 since 10-22 16:00) |

The user had to ask about progress in **31 status episodes**, for example "etat des lieux", "alors?",
"Tu es sûr qu'il est pas bloqué ?" and "tu es sur je vois 0 agents en cours".
There were 52 "merged" notifications, each followed by a manual rebase, land or relaunch cascade.

The main session sent **109 SendMessage relays** (tool ids deduplicated):

| Relay purpose | Count |
|---|---|
| merge, rebase or land | 21 |
| process or rule changes | 20 |
| user decisions | 18 |
| new CR or scope | 15 |
| stuck, nudge or resume | 13 |
| other | 22 |

It also made 44 Agent launches and 15 TaskStops, and opened about 28 CRs (candidates for `crf open`).

**The main session stepped in for a failed or stuck child about 30 times:**
- 7 orchestrator TaskStops, 2 driver kills and 5 replacement orchestrators (Oct 22).
- Nudges at 10-22 21:10 and 21:38, 10-26 16:54 (×2) and 10-26 20:08.
- 2 rate-limit resumes, 1 restart after the API death, and 4 resumes of the P1 orchestrator.
- **Child work done itself:**
  - committed CR 041 round 4 (`9243cf5`)
  - rebased #42, then merged #39 and #42
  - diagnosed the regression (10-26 04:31) and ran 3+3 parallel heavy bisect runs
  - wrote the base-cycle repair instructions
  - launched the CR 123 round 6 driver directly

**Overnight while the user slept (10-26 22:48 to 10-27 06:20):** 25 wakeups, 49 turns, $5.25.
The main LLM made these decisions on its own:
- granted rounds 4 and 5 to CR 123
- re-ran heavy CI
- moved 123 to the top of the stack
- repaired the #128/#129 base cycle
- bisected twice
- started CR 115 rounds on Opus

The stack was green at 06:24. Under the sketch, all of this would have waited for the morning as "blocked" *(inferred)*.

---

## Part C — Where judgment must live

| Holder | Judgment that stays with an LLM | Evidence |
|---|---|---|
| **Coder** | Spec gaps, autonomous decisions, semantic conflict resolution in its own diff | Rows 9, 3 (semantic part) |
| **Reviewer (per-CR agent)** | Evidence match, test-weakening check, "is this failure mine", writing questions with recommendations | Rows 13, 10, 2 (residual) |
| **Sleeping run conductor** (woken by `crf watch` on blocked or red events, cheap model, no polling) | Cross-CR regression attribution after a mechanical bisect; granting extra rounds within a delegated budget; stack reorder; flake vs real regression once the rules give no answer; resume decisions after an API death | Rows 8, 12, 14; overnight 10-26 episode; 65-min idle after the 10-27 API death |
| **Chief-of-Staff main session** | User decisions, scope, new CRs, out-of-budget rounds, external dependencies; reads one `crf status` digest instead of 127 status-read turns | Part B |

**Becomes a `crf` rule:**
- dev-ci hang detection with K re-runs, and a known-flake list or a base-red check
- union merge, count and index regeneration, and ID allocation at open time
- a baseline gate on the base branch at run start (run-level stop)
- a private `npm ci` when dependencies change, with a read-only shared tree
- a window-lock queue, with screen-lock detection that falls back to heavy-CI proof
- squash without `reset`, and land plus cleanup inside `crf land`
- merge detection with automatic restack
- `crf render` state derived from gh, git and round files
- dead-coder detection and resume
- heavy-CI bisect over stack prefixes
- shell helpers (sed, quoting)

**Rare enough to accept as blocked:**
- first-time forge surprises
- external dependency releases (122)
- non-reproducible bugs (121, 134)
- rounds beyond the delegated budget
- shared-resource permission denials that need the user (the 11:59 authorization)

**Where the transcripts refute or amend the sketch:**
1. **"Infra failure gets one re-run" is too tight.** It would have blocked about 7 of 12 CRs on the Oct 22–23 night, all on one infra cause. Allow a per-CR re-run budget, and add a run-level circuit breaker: after N infra failures across CRs, stop the run once with one cause.
2. **Environment drift needs a run-level stop, not per-CR blocks.** Run 2 would have produced 7 identical blocks. A baseline gate on the base branch catches it at minute 0.
3. **Heavy-CI failure attribution on a stack is unspecified.** It happened 6 times. The bisect is mechanical, but choosing the culprit and the fix CR needed an LLM each time.
4. **"Unknown → blocked" stalls overnight runs.** In 10-26 night the main LLM made 6 kinds of decisions that unblocked the stack by 06:24. Without a sleeping conductor holding a delegated round and re-run budget, the run waits about 7 hours *(inferred)*.
5. **The sketch holds up on these points:**
   - Dropping the orchestrator, driver, stack-driver and task-driver LLMs removes **about $235 of subagent cost** and most of the **about 504 turns and $54** of main-session orchestration.
   - It also removes the whole "dead child" failure class (7 freezes, 7-child API death).
   - None of those roles made a decision that a rule, the coder, the reviewer or a conductor could not have made.
   - Stack drivers mostly did conflict resolution: "Keep both".
   - Drivers mostly re-ran CI and relayed messages *(inferred from row frequencies)*.
