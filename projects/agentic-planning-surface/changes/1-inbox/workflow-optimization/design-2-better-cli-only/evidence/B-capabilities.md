# B — Capabilities of the current factory, and what design 2 keeps

Read-only study of the real Claude Code transcripts from 2026-10-17 to 2026-10-27 (UTC).
Sources: main session `dd375646-4450-4e52-a643-89ff1d9e405a.jsonl` and its 1,150 subagents
(`…/subagents/agent-<id>.jsonl` plus `.meta.json`), the other sessions in the window for the
nesting count (session `c985a2ca` is excluded), the Studio run files in
`markdown-okf-schema-studio/.agents/changes/03-requests/` and `04-archives/`, the skill
`change-request-factory`, and the design-1 evidence (`02-dynamics.md`, `03-judgment.md`,
`04-mechanisms.md`, `01-costs.md`). Those findings are reused, not recomputed, except where this
file says so.

**Design 2** as tested: all layers stay LLM agents. Chief of Staff (main session, talks with the
user, no longer orchestrates) → **Foreman** (ex-orchestrator) → **Driver** per CR (CR, stack, task
driver and integrator variants) → **Coder** and **Inspector** (ex-reviewer). Token cuts come from
`crf` (mechanical work in one call), waits outside the LLM (background `crf wait` that notifies on
exit; `/loop` or cron self-wake for the Chief), a file mailbox `crf msg <agent>` that the waiting
agent's `crf wait` also watches, small contexts (schema hand-backs, `crf status`, Foreman rotation
with state handover), TTL and model choices.

Lines marked *(inferred)* are my interpretation. Everything else is quoted or counted.

## 0. Summary

1. **44 distinct capabilities** were exercised or relied on (§2). Design 2 keeps 38 as they are or
   better (cheaper and more reliable). **Two are at high risk** and four at low or medium risk.
2. **The finding that changes design 2: nested `Agent` calls block.** No spawn made by a subagent
   in the window returned at once. **783 of 783** completed spawns by orchestrators, drivers, stack
   drivers and task drivers returned only with the child's hand-back. `run_in_background: "true"`
   made no difference. The main session got `async` on all 163 of its spawns.
   - While a spawner waits, its tool round stays open. No message and no background-command
     notification reaches it before the **whole parallel batch** returns. Example: in
     `agent-a21e1ec0a8fc37d31.jsonl`, a task notification was queued at 16:53:38 and read at
     17:19:37.
   - Orchestrators spent **57.5 h of 78.8 h** of their idle time inside open `Agent` calls. Drivers
     spent 50.4 h of 94.4 h.
   - So design 2's "a waiting agent always has a background `crf wait`, delay ≈ seconds" is true
     only when the Foreman holds no open `Agent` call. A Foreman that spawns its Drivers with the
     `Agent` tool is in exactly the state that lost messages today.
3. **Delivery** (§3), for the 154 messages sent to factory roles:

   | Case | median | p90 | late >30 min | never delivered |
   | --- | --- | --- | --- | --- |
   | Today | 109 s | 77 min | 25 | 15 |
   | Main → orchestrator only (89 messages) | 8.5 min | 2.5 h | 25 | 14 |
   | Design 2, if no agent holds an open `Agent` call | ≈5 s | ≈5 s | 0 | 0 |
   | Design 2, if the Foreman still spawns Drivers with `Agent` | 8.5 min | 2.5 h | 25 | 0 |

   - In the "no open `Agent` call" case, the extra wake-ups cost about **75 wakes, $20 in the
     window**. Add **303 wakes, $36** if the Foreman wakes once per finished child instead of once
     per batch.
   - In the "still spawns with `Agent`" case, main → orchestrator delays do not improve. The
     mailbox does remove the losses: a message is read at restart, about 15 min later at the
     median.
4. **Takeovers** (§4): there were 28 episodes where the main session killed, restarted, nudged or
   did the work of an orchestrator or driver. By root cause:

   | Root cause | Episodes |
   | --- | --- |
   | Child blocked in `Agent` calls, read as "froze" or "lost message" | 11 |
   | The user asked the main session to act (merge, commit, rebase) | 7 |
   | Missing tool or rule (bisect, base check, render, add a round, deps) | 5 |
   | Rate limit or API death | 3 |
   | Permission denial | 2 |
   | Process change | 2 |

   Design 2 removes the tool, rule and restart causes. It removes the "blocked" class only if the
   Foreman stops holding `Agent` calls.
5. **Nesting** (§5): the real maximum was **depth 3**: main → orchestrator → driver →
   coder/reviewer/conflict fixer, with 324 agents at depth 3 and none deeper. Depth-3 agents made
   **0** `Agent` calls, since the tool is withheld at the limit. Design 2
   (Chief → Foreman → Driver → Coder/Inspector) fits the documented default limit of 3
   **exactly**, with no headroom:
   - a Driver must never spawn task drivers (that puts coders at depth 4);
   - Coders keep no subagents of their own, as today.

   The concurrency cap of 20 live subagents was hit once (10-25 10:50). Factory runs peaked at 14.

## 1. Method and scripts

Scripts are in `research2/scripts/B/`. Data is in `research2/data/B/`.

| Script | Does |
| --- | --- |
| `nesting.py` | `spawnDepth` and parent chains from all `.meta.json` files in the window |
| `depth3_spawn.py` | tools used by depth-3 agents; any `Agent` attempt |
| `timelines.py` | per factory agent (167): assistant messages (first/last ts, context, tools, background flag), queued commands, notifications, tool results |
| `agent_block.py` | every `Agent` call: background flag, time the tool round stayed open, result kind (async / returned-report / error) |
| `gaps.py`, `gap_hist.py` | idle gaps between tool rounds by role and by what the agent waited on |
| `deliver_sim.py` | real delays of the 232 classified factory messages (design-1 `facrows.pkl`), recipient state at send time, design-2 simulation, wake-up cost, never-delivered list, per-child wakes |
| `takeovers.py`, `around.py`, `quotes.py` | main-session TaskStop, re-briefs and child work; quotes around timestamps |
| `concurrency.py` | peak live subagents per run |

**Simulation rules** (`deliver_sim.py`).

- **Recipient state.** For each message, the recipient's state is the tool its last assistant
  message was waiting on when the message was sent.
- **Two design-2 variants.**
  - *naive*: every wait, including an open `Agent` call, becomes a background `crf wait` that exits
    on a mailbox message. Delay = min(real, 5 s).
  - *real*: nested `Agent` calls still hold the round open, so only Bash waits get the 5 s delay.
- **Cases that do not change.** A message sent mid-turn, or one that resumes a finished agent,
  keeps its real delay in both variants.
- **Wake-up cost.** Prices are those of `01-costs.md`: Opus and Sonnet input 4/2, 5-min write
  5/2.5, read 0.20, output 20/10 $/MTok. A wake is priced as one turn at the recipient's last
  context, plus one re-arm turn and about 600 output tokens. The first turn is a cache rebuild
  (5-min write) if the recipient had been idle more than 5 min, otherwise a cache read. Wakes to
  the same agent within 60 s count once.
- **Run 5 messages #282 and #283.** design-1 saw them still pending at 21:54Z. They were delivered
  with the 21:56:16 hand-back batch (`agent-a725410a2169211f8.jsonl` 21:56:22: "Time to address the
  coordinator's overnight goal and the new CR 148"). They are counted as 58 and 36 min late.

## 2. Capability catalog

**Columns.**
- **Freq**: count in the window (sources: `02-dynamics` §3 categories, `03-judgment` Part A rows,
  or counted here).
- **Owner today**: who actually did it.
- **Evidence**: M = main transcript `dd375646…jsonl`, `agent-<id>` = subagent transcript,
  `#n` = message number in design-1 `fac.tsv`.
- **Design 2**: who does it, with which `crf` command or instruction. `crf` verbs are those of the
  design-2 brief and the design-1 list (§6 of `02-dynamics`).
- **Risk**: ✅ kept, ⚠️ at risk, ❌ lost.

### 2.1 Steering a run in flight

| # | Capability | Freq | Owner today | Evidence | Design 2 | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Add a CR to a live run | 15 B msgs (9 delivered, median 41 min) | main → orchestrator | #283 10-27 21:19 "New CR 148 on top of the stack" (58 min late); #255 "Add CRs 122-124 to the stack" | Chief: `crf add <cr> --top/--after`; Foreman reads it at its next wake | ✅ if the Foreman is reachable (see 41) |
| 2 | Drop or cancel a CR | 2 | main (did it itself) | user 10-26 22:48 "ah la 121 je l'ai corrigé ajd c'est fixé"; M 22:49 "J'ai fermé la 121 et elle sort du stack" | Chief: `crf cancel 121 --reason`; `crf stack` drops it from the chain | ✅ |
| 3 | Reprioritise or focus | 3 | main → orchestrator | #104 10-23 21:21 "User: focus 056, Opus allowed", delivered **8 h 05 min** later | Chief: `crf order` / `crf note --all` | ✅ (latency depends on 41) |
| 4 | Change the scope of a CR in flight (next round) | 19 C msgs | main → orchestrator/driver → coder | #76 "CR 045: user adds file includes, round 2" (50 min late to the orchestrator; 155 s direct to the driver, #77) | Chief: decision in `00-request.md` + `crf note <cr>`; the Driver reads it at the round boundary | ✅ |
| 5 | Redirect a warm coder mid-task (keep its code context) | 3–5 (084 ×3, 045, 041) | orchestrator resumes the **same coder** | #222/#232/#233 10-25 21:02–22:38 "Add list-table row handles", "handles outside the table", "wide scrolling table": coder `agent-abf91f7ea342896ed` resumed each time in 1–6 s | Driver resumes the finished Coder with `SendMessage` (resume keeps the cache, C2). A message to the Driver during a coder round still waits for the round to end (Driver blocked in `Agent`) | ⚠️ low: same as today, not better |
| 6 | Grant extra rounds | 9 C2 msgs; 5 CRs beyond 3 rounds | main decides; orchestrator relays | #56 10-22 20:23 "User grants CR 025 two more rounds" (never delivered); #260 10-27 01:46 "Grant 123 round 4, separate 113 review" (1.4 s) | Chief or Foreman within a delegated budget: `crf grant <cr> rounds=N` | ✅ (night: see 30) |
| 7 | Model escalation (Opus coder) | 17 CRs had an Opus coder (counted from meta) | user/main → driver | #273 10-27 05:23 "CR 115 round 4 on Opus" | Driver rule (2nd FIX-REQUIRED → Opus), overridden by `crf note`/`crf grant --model opus` | ✅ |
| 8 | Process or rule change mid-run | 19 I msgs | main → all | #99 10-23 19:58 "Switch commit trailer to Assisted-by"; #223 "Publish PRs as ready, not draft"; #231 "Branch prefix rename" | Chief edits the rule file + `crf note --all`; open PRs: `crf ship --update-body` | ✅ |
| 9 | Ownership: the user or main takes a branch | 5 M msgs | main | #65 10-23 12:45 "User had r4 committed and pushed early"; #89 "Main session rebased #42 and will merge it" | `crf hold <cr>` / `crf release <cr>` so no Driver overwrites the branch | ✅ |
| 10 | Stand down or coordinate between orchestrators | 3 | main | #88 "Thanks; 047/048 belong to orchestrator B, return now"; #127 "Tell orchestrator I to stand down" | One Foreman per run; state owns the CR → Driver mapping | ✅ (disappears) |
| 11 | Information request to an agent | 8 A msgs (2 status pings to drivers) | main → agent | #92 10-23 16:54 "Status ping from main session" (delivered 27 min later) | `crf status [--notes <cr>]` reads state; free-form question via `crf msg` | ✅ |
| 12 | Unblock (authorisation, locked screen) | 4 F msgs | main/orchestrator → driver | #276 10-27 11:59 "User authorizes just requirements-update" (after user: "oui les agent peuvent lancer `just requirements-update`") | Chief: rules/settings update + `crf note --all`; blocked CR → `crf release` | ✅ |

### 2.2 Stack, CI and integration

| # | Capability | Freq | Owner today | Evidence | Design 2 | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| 13 | Build the stack dynamically, one CR at a time | 4 cases (P1+P2 #64–#109, P1 107–124, run 2 #132–#138, run 5) | orchestrator / stack driver | `agent-aa284441fb21ed442` grew 22 PRs, then #88–#109 | Stack Driver + `crf stack` (order in state) | ✅ |
| 14 | Reorder the stack, red PR to the top | 2 | main decides; stack driver executes | #265 10-27 02:47 "Move 123 to top, round 5"; #248 "Fix goes on top; leave branch names" | Chief/Foreman: `crf stack order …`; Stack Driver rebuilds | ✅ |
| 15 | Repair a base cycle | 1 | main detects; stack driver repairs | #269 10-27 02:59 "PR bases now form a cycle"; M 02:59 "#128 (123) dépend de la 124" | `crf stack check` (base and cycle verification) before every hand-back | ✅ (better) |
| 16 | Restack after merges (land, rebase, prune) | 21 D1 msgs; 52 "merged" notices | main → orchestrator; often main itself | #229 "Rebase stack: PR #91 merged"; user 10-25 21:57 "j'ai mergé. rebase les autre pr" | `crf status --merged` on Chief's loop, then `crf stack sync` by the Stack Driver | ✅ |
| 17 | Base choice by file overlap, cross-CR constraints | 1 run (run 5) | main plans; orchestrator applies | `RUN-BRIEF-addendum-run5.md`; orchestrator: "built ON TOP of CR 140 (same files)" | Chief writes the order in state (`crf stack order`); Foreman passes constraints in Driver prompts | ✅ |
| 18 | Heavy CI on the stack top | 34 dispatches | stack driver / main | `RUN-BRIEF.md` "heavy CI on the branch (`gh workflow run ci.yml --ref <branch> -f heavy=true`)" | `crf ci heavy <branch>` + `crf ci wait` (background) | ✅ |
| 19 | Bisect a red stack with parallel heavy runs | 2 episodes (10-26 03:58, 10-27 03:45/05:04) | **main** | M 10-27 03:45 "Pour trancher, j'ai lancé trois CI lourds en parallèle"; M 10-26 04:31 "J'ai lancé le même test sur `main` pour le confirmer" | Foreman: `crf stack bisect` (mechanical), then attribution by the Foreman with a policy card | ✅ (moves down from the Chief) |
| 20 | Flake vs regression call | 8–10 CRs flaky; 6 cross-CR regressions | driver; main for cross-CR | CR 031 driver "Main itself fails CI often, so I judged both flaky" (`03-judgment` row 2); M 10-26 04:05 "Le blocage n'est pas un problème de machine de CI : c'est une vraie régression" | Rule: untouched by the diff and red on base or on the flake list → flaky (`crf ci classify`); otherwise Inspector/Foreman | ✅ |
| 21 | Infra re-runs (dev-ci hang) | ~10 CRs, 54 reruns, 25 cancels | drivers | night orchestrator 10-23 03:59 "the `dev-ci` step hung for 20 to 60 minutes on nearly every PR" | `crf ci wait` detects a silent step, reruns K times; run-level circuit breaker | ✅ |
| 22 | CI watching | 475 watch/poll commands, 561 `sleep` | drivers, orchestrators, main | `03-judgment` scale table | `crf ci wait` in the background; no LLM poll | ✅ (cheaper) |
| 23 | Conflict resolution on rebase | ~40 rebases with conflicts; 18–21 conflict-fixer agents | stack driver / conflict fixers / integrator | `TASKS.md` T14 "conflict in codeCopy.test.ts and SwRS LIFE-069 resolved keeping both intents" | `crf stack` union-merges append-only files and regenerates counts; the Stack Driver spawns a Coder for semantic conflicts (depth 3, allowed) | ✅ |
| 24 | Split a CR into tasks with task drivers and an integrator | 1 CR (135): 26 tasks, 28 task drivers, 6 integrators | orchestrator (depth 1) → task drivers/integrator (depth 2) | user 10-27 16:21 "fait travailler plusieurs driver en paralleles pour optimiser le dev mais livre qu'une seule PR avec tout"; `RUN-BRIEF.md` "Integrates finished tasks strictly in task order T1 → T26" | Foreman spawns task Drivers and the integrator **directly** (depth 2); `crf task …` state | ✅ only if they stay children of the Foreman (§5) |
| 25 | ID allocation and renumbering on conflict | ≥3 (TABLE-003→007, BLOCK-002→003/004, visual v23-24→v25-26) | stack driver | `03-judgment` row 3 | `crf open` allocates IDs | ✅ |
| 26 | Shared node_modules drift / dependency install | 5 CRs | driver; main on request | user 10-27 15:23 "supprime le worktree CR 123. install le node_modules qu'il faut" | `crf deps sync <cr>` (private `npm ci` when package*.json changes) | ✅ |
| 27 | Window-test lock (exclusive local resource) | 4 contention events; 8 CRs hit a locked screen | drivers, coders | `RUN-BRIEF.md` "Window tests: one task at a time under `WINDOW-TESTS.lock`"; lock content "T18 22:38" | `crf lock take/release`, queue; screen-lock detection switches proof to heavy CI | ✅ |
| 28 | External dependency release (cross-repo) | 1 (122 waits for okf-schema 0.15.0) | user/main | user 10-26 22:22 "j'ai release une nouvelle version de https://github.c…"; M 22:36 tag move denied | Chief: `crf hold 122 --until …`; release stays the user's | ✅ |

### 2.3 Unattended running, resilience and machine

| # | Capability | Freq | Owner today | Evidence | Design 2 | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| 29 | Night autonomy with self-wake | 5 nights; 10-26/27 night: 25 wakeups, 49 turns, $5.25 | main (cron at :17/:47 on 10-27) | M 10-27 21:06 "J'ai programmé une tâche récurrente avec l'outil de planification de Claude Code … à h17 et h47, toutes les 30 minutes" | Chief: `/loop` or `CronCreate` (main only; `ScheduleWakeup` is withheld from subagents, C15) + `crf status` | ✅ |
| 30 | Cross-CR judgment at night (grants, reorder, bisect, Opus) | 6 decisions on 10-26/27 | **main** | `03-judgment` Part B: "granted rounds 4 and 5 to CR 123 … repaired the #128/#129 base cycle … bisected twice" | If the Chief "no longer orchestrates", the Foreman needs a **delegated budget and policy card** (+1 round, red to top, bisect before regrant) and must escalate the rest | ⚠️ medium: policy, not mechanism |
| 31 | "I need the machine" / pause without loss | 3 E msgs (10-24 06:34, 10-26 07:07, 10-27 20:57) | main → orchestrator | user 10-24 06:34 "Arrête les taches dès que tu peux sans perdre de donnée"; #106 delivered in 310 s; F2 resumed from files 15:05 | `crf pause --all` (step boundary) then `crf resume`; Foreman restart from state | ✅ |
| 32 | Keep the machine awake | 4 (10-20, 10-22 20:39, 10-23 17:34, 10-27 20:57) | main / orchestrator | M 10-27 20:58 "J'ai lancé `caffeinate -dimsu -t 43200` en arrière-plan" | `crf awake --hours N` at run start; checked by `crf status` | ✅ |
| 33 | Restart a stuck or dead child from files | ~10 re-briefs, 9 agent TaskStops | main | M 10-22 20:53 "L'orchestrateur restait figé depuis 25 minutes … Je l'ai arrêté, ce qui a aussi arrêté les drivers de 025 et 029" | Heartbeat + `crf status`; Foreman restart from state + events. **Killing a Foreman kills its live Drivers** (7 drivers died in 5 kills, measured) | ⚠️ high: see 42 |
| 34 | Resume after a rate limit / session limit | 2 (K, L) + 3 at 10-22 | main | #155 10-25 06:59 "Resume K after the rate limit" | `SendMessage` resume keeps the history (C2); the Chief's cron detects it | ✅ |
| 35 | Recover from an API death that took 7 children | 1 (10-27 18:05) | main, only after the user typed "contineu" at 19:13 | M 10-27 18:08 "Failed to authenticate. API Error: 403 Internet Security by Zscaler"; 19:14 "J'ai relancé l'orchestrateur. Il s'était arrêté sur une erreur d'API" | Chief cron keeps firing and retries; `crf status` shows dead agents; restart from state | ✅ (65 min → ≤30 min) |
| 36 | Concurrency slots (max drivers, max open PRs) | user 10-27 10:39 "lance 4 CR max en parallele"; cap 20 hit once | orchestrator | `RUN-BRIEF-addendum-run5.md` "up to 4 task drivers … plus up to 2 CR drivers"; `agent-a14fa7d64e7b029f2` 10-25 10:50 "Concurrent subagent limit reached. You can run 20 subagents at once" ×20 | `crf slots N`; slots must count every live agent of the session (peak 14 in runs) | ✅ low risk |
| 37 | Permission-denial reporting (never work around) | ~7 child events + 4 main denials | all roles | `TASKS.md` T1 "revert denied, for the user"; `agent_block` 10-27 15:14 Agent spawn denied "[Git Destructive]" | Record via `crf deny <cr> "<cmd>"`; `crf land` writes a cleanup script for the user | ✅ |

### 2.4 User-facing work of the Chief

| # | Capability | Freq | Owner today | Evidence | Design 2 | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| 38 | Status questions | 31 status episodes, 127 status-read turns ($17.5) | main | user 10-25 15:41 "tu es sur je vois 0 agents en cours"; 10-23 16:53 "Tu es sûr qu'il est pas bloqué ?" | Chief: one `crf status` call (links, heartbeats, unread mailbox ages) | ✅ (cheaper) |
| 39 | Backlog filing and triage (P1–P4, inbox) | dozens of user requests | main | user 10-27 07:24 "tu notes ca comme un bug en P1 on corrigera plus tard"; 09:37 "fix later en P1" | Chief (`crf backlog add`, or skill only) | ✅ |
| 40 | Grill once for a whole night batch | ≥4 sessions | main | user 10-25 21:11 "identifie les CR qui a besoin de questions/reponses que tu va me poser maintenant et enregistrer les reponses dans les dossier des CR pour que tu traites tout cette nuit" | Chief | ✅ |
| 41 | Talk to a running Foreman or Driver at any time (the user relies on it through the Chief) | 103 main → factory messages | main → orchestrator/driver | `02-dynamics` §2; 16 lost, 23 >30 min | Mailbox + background `crf wait`. **Holds only while the agent holds no open `Agent` call** (§3) | ⚠️ high |
| 42 | Replace or rotate the orchestrator without losing work | 5 replacements (10-22), J replaced I, F → F2 | main | M 10-23 07:25 "Orchestrator: stacked PRs" replaced the rebase orchestrator | Foreman rotation with state handover. **A subagent cannot finish while its children run**, and TaskStop kills them, so rotation only works at quiescent points if Drivers are `Agent` children | ⚠️ high |
| 43 | Landing (archive, report, worktree cleanup) | 107 archived CRs (024–150) | orchestrator; often main | M 10-22 18:57 "Land CR 027: report, archive, remove worktree"; 10-23 17:48 "Land CR 047 …" | `crf land <cr>` (+ cleanup script for denied commands) | ✅ |
| 44 | Demo tour of a green stack | 1 (10-27 06:27–09:20), then made a rule | main | M 10-27 06:27 "Ouvre ce fichier : … tour.md"; 06:43 "J'ai ajouté une règle « Demo tour »" | Chief (needs the user live) | ✅ |

The skill also covers these, folded into the rows above:
- merge **on explicit user request**: 10-23 08:31 "tu vas tout merger", 10-24 15:33 "please merge
  all"; the Chief does it, as today;
- evidence and before-shot checks: user 10-26 20:35 "on voit que l'agent n'a pas reproduit mon
  probleme"; #252; Inspector rule;
- "Autonomous decisions" and questions with recommended answers: about 27 and 22 CRs; Coder and
  Inspector;
- PR body for an external reader: user 10-23 13:55; #184.

## 3. Message delivery

### 3.1 Idle gaps between tool rounds (`gap_hist.out`, `gaps.out`)

161 factory agents, 4,048 gaps:

| Gap | Orchestrators: n / time | Drivers (CR, stack, task, integrator): n / time |
| --- | --- | --- |
| < 10 s | 706 / 1.0 h (1 %) | 1,642 / 2.4 h (3 %) |
| 10–60 s | 203 / 1.4 h (2 %) | 523 / 3.4 h (4 %) |
| 1–5 min | 136 / 6.1 h (8 %) | 526 / 29.7 h (31 %) |
| 5–15 min | 59 / 8.6 h (11 %) | 127 / 18.5 h (20 %) |
| 15–60 min | 43 / 21.3 h (27 %) | 59 / 28.5 h (30 %) |
| 1–3 h | 12 / 21.6 h (27 %) | 9 / 12.0 h (13 %) |
| > 3 h | 3 / 18.9 h (24 %) | 0 |

Per role: orchestrator p50 7 s, p90 5.1 min, p99 90 min, max 8.6 h. Driver p50 8 s, p90 4.9 min,
p99 36 min, max 2.6 h. **The median gap is seconds, but 89 % of an orchestrator's idle wall time
sits in gaps over 5 min**: 70 h of 79 h. For drivers it is 66 %.

What the agent was waiting on during gaps over 5 min:

| Waiting on | Gaps >5 min | Median | Max | Hours |
| --- | --- | --- | --- | --- |
| An open `Agent` call (blocking, see below) | 217 | 15 min | 8.6 h | 99.7 |
| Turn ended (waiting for a notification or a resume) | 12 | 22 min | 6.6 h | 12.2 |
| After a hand-back (resumed later) | 11 | 48 min | 74 min | 7.6 |
| Foreground Bash `sleep` / watch | 38 | 9 min | 10 min | 5.2 |
| Other foreground Bash | 30 | 9 min | 10 min | 4.1 |
| Foreground gate (tests) | 4 | 10 min | 10 min | 0.6 |

**Nested spawns block** (`agent_block.out`).

| Spawner | Spawns | Returned only with the child's report | Async | Tool round open: median, p90, max |
| --- | --- | --- | --- | --- |
| Orchestrators | 449 (121 with `run_in_background: "true"`) | all | 0 | 3–13 min, 17–77 min, 8.6 h |
| Drivers | 221 | all | 0 | 2–7 min, 20–35 min, 2.6 h |
| Task drivers and stack drivers | 106 | all | 0 | |
| Main session | 163 | — | **163** | 1–4 s |

- Each child's result reads: "This agent's report was delivered to you as a message from "…" (its
  SubagentHandback call)".
- The docs say subagents spawned from the main conversation start in the background. For nested
  spawns they say only that, in interactive sessions, "a subagent that launches background
  subagents waits for their results before it finishes". For `claude -p` they add that nested
  subagents start in the background only with fork mode off (`CLAUDE_CODE_FORK_SUBAGENT=0`).
- In this VS Code session with defaults, every nested spawn behaved as foreground. Whether fork
  mode off changes this in interactive sessions is **not documented and not tested**
  *(to verify)*.

### 3.2 Real delays vs design 2 (`deliver_sim.out`)

Delays are median / p90 / count over 30 min.

| Messages | n | Never delivered | Today | Design 2 naive | Design 2 with blocking `Agent` calls |
| --- | --- | --- | --- | --- | --- |
| main → orchestrator | 89 | 14 | 8.5 min / 2.5 h / 25 | 5 s / 5 s / 0 | 8.5 min / 2.5 h / 25 |
| main → driver, stack or task driver | 14 | 0 | 2.1 min / 20.5 min / 0 | 5 s / 5 s / 0 | 5 s / 20.5 min / 0 |
| agent → orchestrator (reports) | 35 | 0 | 82 s / 4.6 min / 0 | 5 s / 7 s / 0 | 5 s / 4.5 min / 0 |
| orchestrator → driver | 16 | 1 | 3 s / 2.5 min / 0 | 3 s / 7 s / 0 | 3 s / 7 s / 0 |
| All dynamic (categories A–M) | 119 | 15 | 2.6 min / 116 min / 25 | 5 s / 5 s / 0 | 40 s / 116 min / 25 |

Recipient state at send time, for the 124 messages to orchestrators (89 from main, 35 reports):

| State | Messages |
| --- | --- |
| In an open `Agent` call | 58 |
| Killed later while in an open `Agent` call (never delivered) | 14 |
| In a Bash wait or another Bash call | 32 |
| Resumed after a hand-back | 12 |
| Turn ended | 6 |
| Mid-turn | 2 |

**All 15 never-delivered messages** (#46–58, #61, #64) went to an agent blocked in an `Agent`
call that was later killed. Under design 2 the mailbox would have held them for the replacement.
In the real restarts, the replacement started **15 min (median), 45 min (max)** after the send.

**Wake-up cost** (01-costs prices, window of 7.6 days):

| Variant | Extra wakes | Of which cache rebuilds | Median context | Cost in the window |
| --- | --- | --- | --- | --- |
| Naive: one wake per mailbox message | 75 | 50 | 81k | **$20.08** (about $18/week) |
| Naive, plus one wake per finished child instead of one per batch (89 batches, 392 children) | +303 | — | — | **+$35.55** |
| Blocking `Agent` calls: only Bash-wait states wake | 22 | — | — | $4.63 |

- **Batching the child wakes.** `crf wait --all|--any N` can batch child completions and avoid
  the +303 wakes *(inferred)*.
- **The largest single wakes** are the P1+P2 orchestrator at 325k–354k context, Sonnet, about
  $0.9 each. Rotating the Foreman at about 100k would cut them by about 3× *(inferred)*.

**Verdict for task 2.**
- *If no agent holds an open `Agent` call*, the mailbox and `crf wait` do turn today's
  "minutes to hours, 15 lost" into seconds, for about $20–55 per window.
- *With the current spawning model*, the Foreman is unreachable for the whole life of its Driver
  batch, exactly as today. The mailbox only converts "lost" into "read at restart".

## 4. Takeovers by the main session (since 10-22 16:00)

Sources: `03-judgment` Part B, `takeovers.out` (TaskStop, re-brief spawns, git and gh actions by
main), and the text around each one (`around.py`).

| # | When (UTC) | What main did | Root cause | Evidence |
| --- | --- | --- | --- | --- |
| 1 | 10-22 16:19 | Killed "Orchestrate all open PRs", re-briefed 16:21 | Blocked in an `Agent` call (#46–48 lost) + tree misunderstood | user 16:11 "tu as bien un sous agent chacun sur le coup pour les fixers"; M 16:11 "aucun sous-agent ne corrige la #15 ni la #16" |
| 2 | 10-22 17:21 | Re-spawned the orchestrator | Rate limit ("session limit · resets 7:20pm") | `agent_block` 16:22 error |
| 3 | 10-22 18:57 | Landed CR 027 itself | Lost message (#49), orchestrator blocked since 17:22 | `takeovers.out` 18:57 "Land CR 027: report, archive, remove worktree" |
| 4 | 10-22 19:38–19:41 | Killed the orchestrator, spawned drivers 028/029 itself, killed them 3 min later, landed 024/026 | Blocked (#49–51 lost); user "etat des lieux" | M 19:38 "J'arrête l'orchestrateur bloqué et je relance moi-même les drivers" |
| 5 | 10-22 20:24 | Killed "CRs 024-029" (6 messages lost) | Blocked, misdiagnosed as `rm -i` | M 20:22 "Il est sans doute bloqué sur un `rm -i`" |
| 6 | 10-22 20:53 | Killed "responsive rules" (and its 2 drivers) | Blocked | M 20:53 "restait figé depuis 25 minutes … ce qui a aussi arrêté les drivers de 025 et 029" |
| 7 | 10-22 21:10 / 21:38 | Nudged the night orchestrator (delivered after 117 / 88 min) | Blocked in 4 foreground driver calls | `02-dynamics` §2 |
| 8 | 10-23 07:24 | Replaced the rebase orchestrator with a stacked-PR one | User process change | user 07:21 "Utilise la stp" (stacked PR) |
| 9 | 10-23 08:31–08:39 | Killed it; cancelled the hung run, admin-merged, `gh stack merge` | User-delegated merge + CI hang | user 08:31 "Pour moi tu vas tout merger"; 08:36 "N'attend pas les pipelines" |
| 10 | 10-23 09:24 | Killed "land 10 CRs + 041", re-briefed | Lost message (#61) + new priority | user 09:23 "concente toi pour les fixer" |
| 11 | 10-23 12:45 | Committed and pushed CR 041 r4 and the stress-advisory change | User impatience; driver ping #64 lost | user 12:42 "c'est trop long il faut passer à la vitesse superieur" |
| 12 | 10-23 15:43–16:28 | Merged #39 and #42, rebased #42 and #43 itself | Late messages (46–185 min) + relays to guessed names failed + delegated merge | M 15:45 "son driver ne fait qu'attendre la CI. Je fais le rebase moi-même" |
| 13 | 10-23 16:44–20:44 | Landed 049, 052, 047, 048, 051, 053; ran a 5-min status-render script | Orchestrators unreachable; status stale (missing render tool) | M 17:48 "se régénèrent maintenant toutes les 5 minutes … même si un orchestrateur se bloque" |
| 14 | 10-24 15:34–16:23 | Merged #51–#54, rebased 057/058/#54, landed 056–058 | Delegated merge; no live orchestrator *(inferred)* | user 15:33 "please merge all" |
| 15 | 10-24 19:34 | J replaced I | Coordination | #127 |
| 16 | 10-25 06:59 / 12:04 | Resumed K and L | Rate limit | #155, #183 |
| 17 | 10-25 15:59 / 17:04 | Rebased PR 63; merged PR 70 | User request; the driver had returned | user 15:59 "c'est bon rebase 63" |
| 18 | 10-26 03:44–04:31 | Heavy CI on top, bisect over 4 branches and main, regression call | Missing bisect tool + cross-CR judgment kept at main | M 04:31 (regression diagnosis) |
| 19 | 10-26 06:23–06:26 | Fixed the #89/#92 bases, unstack/relink, merged the stack | Forge surprise + delegated merge | user 06:24 "je veux toutes les merger" |
| 20 | 10-26 16:54 ×2, 20:08 | Nudged / relaunched the P1 orchestrator | Stalled in `Agent` calls (#250, 16 min) | M 20:08 "l'orchestrateur était à l'arrêt depuis plus d'une heure" |
| 21 | 10-26 22:37–22:49 | Wrote the stack order in `P1-RUN-BRIEF`; archived 121 itself | Orchestrator unreachable (#255/#256 were 52/41 min late) | M 22:49 "J'ai fermé la 121" |
| 22 | 10-27 02:59–05:04 | Diagnosed the base cycle, wrote the repair, bisected with 3 heavy runs | Missing base-check and bisect tools | M 03:45 "j'ai lancé trois CI lourds en parallèle" |
| 23 | 10-27 09:59 | Worktree and branch cleanup; delete denied | Landing after the run ended + permission denial | `takeovers.out` 10:00 DENIED |
| 24 | 10-27 10:10 | Spawned "Driver CR 123 round 6" itself | No live orchestrator; no "add a round" path | `takeovers.out` 10:10 |
| 25 | 10-27 15:23 | Removed the 123 worktree; `npm install --no-save shiki` | User request + node_modules drift (missing tool) | user 15:23 |
| 26 | 10-27 16:18 | Cleanup denied "[Git Destructive]" | Permission denial | `takeovers.out` 16:18 |
| 27 | 10-27 19:14 | Restarted the orchestrator after the API death | API death (main died too, 18:08); no wake source | user 19:13 "contineu" (65 min idle) |
| 28 | 10-22 → 10-27 | 9 agent TaskStops (7 orchestrators, 2 drivers), 7 drivers killed with them | Consequence of 1–7, 9, 10 | `takeovers.out`; children "[Request interrupted by user for tool use]" |

**Causes, and what design 2 does about each**

| Cause (episodes) | Design-2 mechanism | Residual risk |
| --- | --- | --- |
| **Child blocked in `Agent` calls, read as "froze" or "lost message"** (1, 3–7, 10, 12, 13, 20, 21 = 11) | Mailbox: no message is lost. `crf status` shows "Foreman busy in N Driver calls; mailbox: 3 unread, oldest 40 min", so the Chief no longer kills a healthy Foreman by mistake | **High.** Latency is unchanged, because the Foreman cannot read before the batch returns. Fix: the Foreman never holds `Agent` calls. Either Drivers are launched outside the `Agent` tool (`crf spawn` → background `claude -p` session, cross-session inbox or mailbox), or the Chief spawns Drivers (async) at the Foreman's request, or fork mode off is proven to make nested spawns async *(to verify)* |
| **User asked main to act: merge, commit, rebase** (9, 11, 12, 14, 17, 19, 25 = 7) | Merging on request is the Chief's job (the user's agent). `crf hold <cr>` before the Chief or the user touches a branch; `crf status` with an ETA answers impatience | Low. The Chief still does some of this work, by design |
| **Missing tool or rule** (13, 18, 22, 24, 25 = 5) | `crf render`, `crf stack bisect`, `crf stack check`, `crf grant`/`crf round add`, `crf deps sync` | Low. Attribution after a bisect still needs an LLM (Foreman, with a policy card) |
| **Rate limit or API death** (2, 16, 27 = 3 episodes, 4 events) | Chief cron (as on 10-27 night, every 30 min) + heartbeats in `crf status`; resume by `SendMessage` (history kept) or restart from state | Medium. A network-wide 403 kills every layer at once; the cron retries, so the worst case drops from 65 min to about 30 min |
| **Permission denial** (23, 26 = 2) | `crf land` writes a cleanup script for the user; denials are recorded per CR | None (by rule, the user runs it) |
| **Process change** (8, 15 = 2) | Rules file + `crf note --all`; Foreman rotation at a quiescent point | **Medium.** Rotation kills live Drivers if they are `Agent` children (episode 6, measured) |

## 5. Nesting

**Real depth** (`nesting.py`; `spawnDepth` agrees with the parent chains):

| Session | Depth 1 | Depth 2 | Depth 3 | Deeper |
| --- | --- | --- | --- | --- |
| `dd375646` | 332 | 494 | 324 | 0 |
| `521459c8` | 6 | 0 | 0 | 0 |
| `1275de24` | 35 | 0 | 0 | 0 |

- **Typical chain:** "CR123 coder round 1 ← Driver CR 123 ← P1 stack orchestrator ← main".
- **By factory role:**

  | Role | Depth 1 | Depth 2 |
  | --- | --- | --- |
  | Orchestrators | 31 | 0 |
  | CR drivers | 7 (spawned by main) | 90 |
  | Stack drivers | 0 | 5 |
  | Task drivers | 0 | 28 |
  | Integrators | 0 | 6 |

- **Depth-3 agents** (coders, reviewers, conflict fixers) made **0** `Agent` calls. They used
  Bash ×10,170, Monitor ×262 and SubagentHandback ×318.
- **The `Agent` tool is absent at depth 3.** No "Available agent types" listing appears in
  depth-3 transcripts; it does appear at depth 2.
- **This matches the docs:** "a subagent can spawn subagents of its own, up to three layers below
  the main conversation. At the depth limit, Claude Code withholds the `Agent` tool"
  (`cc-sub-agents.md` §"Let subagents spawn their own subagents"). The setting is
  `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, default 3.
- **Nothing broke on depth.** No agent tried to go deeper.

**Design 2 fits, with no headroom.**

| Layer | Depth |
| --- | --- |
| Chief | 0 |
| Foreman | 1 |
| Driver (CR, stack, task driver, integrator) | 2 |
| Coder, Inspector, conflict fixer | 3 |

Constraints:
- **Task drivers and the integrator must be children of the Foreman**, as today. A CR Driver that
  spawns task drivers would put Coders at depth 4, without the `Agent` tool. That works only if the
  task driver codes itself, which breaks "never move a task up".
- **Coders and Inspectors cannot use helper subagents** (Explore, verifiers), the same as today.
- **Raising the limit** to 4 is possible with the setting, but no run needed it.
- **If Drivers become separate `claude -p` sessions** (the fix of §4), every Driver tree starts
  again at depth 0. Coders would then gain one layer.

**Other limits that touch the same tree:**
- **Concurrent subagents.** The cap is 20 live subagents per session (default). It was hit once,
  by Orchestrator L spawning SwRS writers 21–42 (10-25 10:50, 20 refusals: "Do not retry"). Factory
  peaks per run were 12, 4, 9, 11 and 14 (run 5: 7 drivers and 6 coders). `crf slots` must count
  the Chief's own side agents too.
- **No self-wake below the Chief.** Subagents do not get `ScheduleWakeup` and `Workflow` (C15), so
  only the Chief can `/loop` or use cron. The Foreman and Drivers wait with background Bash
  (allowed, notified on exit, C26, no time limit locally, C27); 10 such notifications were
  observed in factory agents.

## 6. Capabilities at risk, and what design 2 needs to keep them

| Risk | Capability (§2) | Why | What design 2 needs |
| --- | --- | --- | --- |
| **High** | 41 Talk to a running Foreman/Driver quickly; 1, 3 latency of add/focus | Nested `Agent` calls block the tool round (783/783 measured); `crf wait` notifications queue behind them (16:53:38 → 17:19:37) | The Foreman never holds an `Agent` call open: `crf spawn` launches each Driver as a background headless session, or the Chief spawns Drivers on a Foreman request. Test `CLAUDE_CODE_FORK_SUBAGENT=0` first |
| **High** | 33, 42 Restart or rotate the Foreman without losing Drivers | A subagent cannot finish while its children run; TaskStop kills them (7 drivers killed in 5 kills) | Same fix. Otherwise, rotate only when no Driver is live, and make every Driver resumable from state (they were: "025 et 029 reprennent depuis leurs en-têtes") |
| **Medium** | 30 Cross-CR judgment at night | All 6 overnight decisions on 10-26/27 were the main session's; design 2 says the Chief no longer orchestrates | A policy card and delegated budget for the Foreman (+1 round, red to top, one rerun, bisect before regrant); the Chief keeps only out-of-budget calls. Or keep the Chief as night judge via cron |
| **Low** | 5 Redirect a warm coder mid-round | The Driver is blocked in the coder's `Agent` call; the message reaches the coder only after the round (as today) | The Driver resumes the same Coder with `SendMessage` (cache kept). Same as today, not better |
| **Low** | 24 Task split | Fits only at depth 2 under the Foreman | State this in the Foreman card |
| **Low** | 36 Slots | Cap of 20 per session | `crf slots` counts all live agents |

## 7. Caveats

- **Role inference.** Roles come from descriptions (regex, as in design 1).
- **Delivery timestamps.** The delivery time is the timestamp of the queued attachment or the user
  turn. 997 of 1,157 queued attachments sit within 10 s of the next turn. 92, mostly task
  notifications, were written earlier than they were read. So delivery times are close to
  consumption times, but slightly early.
- **The 5 s wake in the simulation is an assumption.** It stands for the poll interval of
  `crf wait`, the harness notification and the start of the next turn.
- **Costs are proxy prices from `01-costs.md`.** Wake costs exclude the work a message triggers,
  which happens in both designs.
- **Run 5 is still live.** The data was read up to 22:05Z on 10-27.
- **Takeover causes.** Causes are assigned from the main session's own words next to each
  action. Where two causes apply, the first listed one counts. "No live orchestrator" in episodes
  14 and 24 is *(inferred)*.
