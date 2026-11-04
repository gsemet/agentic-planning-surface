# 02 — Dynamics: how the user steered running factory agents (2026-10-17 → 2026-10-27)

Read-only study of real Claude Code transcripts, to judge what the design sketch
(`03-design-sketch.md`, sections 3, 4, 13) keeps, moves or loses of the "talk to a running agent"
flexibility.

## 0. Summary

- **283 SendMessage calls** in the window in the main session tree (deduplicated by tool-use id),
  plus 7 in one other session. **232** involve a factory role (orchestrator, CR/task driver,
  stack driver, integrator). Of these, **130 are "dynamic"** (they change the plan, the
  scope, the rules or the stack). The other 102 are the factory's normal plumbing: round dispatch
  to coders and reviewers (64), plus reports sent back up (38).
- On top of that, the main session **killed 9 factory agents** with TaskStop (7 orchestrators, 2 drivers) and
  **re-briefed or restarted about 10** with a new Agent call. It did this whenever messages stopped
  landing.
- **Key mechanical finding.** A message to a running subagent arrives only at that subagent's next
  tool round. An orchestrator blocked in parallel foreground `Agent` calls, or parked while it waits
  for background drivers, got nothing until a driver returned. Of **89 main → orchestrator
  messages**, **16 never arrived** and **23 arrived more than 30 minutes late** (worst 8 h 05 min).
  The median delay was 6.4 min. Of **14 main → driver messages**, none was lost: median 2 min,
  maximum 27 min.
- **Where the flexibility really sat.** The user only ever talks to the main session. The main
  session recorded most decisions in files first: 66 of 103 messages point to an
  `00-request.md` decision, a brief or a state file. Then it nudged an agent, did the work itself
  (merges, rebases, landing, bisect), messaged a driver directly, or killed and re-briefed the
  orchestrator. Every decision that judged across CRs came from the main session; the
  orchestrators only relayed and executed them. Examples: round grants, "red PR goes to the top",
  bisecting the heavy CI, and the stack order in `P1-RUN-BRIEF.md` and `RUN-BRIEF-addendum-run5.md`.
- **Stack built dynamically: true, and done by LLM executors.** The P1+P2 orchestrator (10-25/26)
  grew a 22-PR stack, then a night stack (#88 to #109), one CR at a time. It absorbed 3 moves of
  main, the user merging 22 PRs, a branch-prefix change and "fix goes on top". The P1 stack driver
  (10-27 night) took 7 resumes: append, reorder, absorb fix commits, and repair a base cycle that it
  had created itself. Its context was valuable for *execution state*: commits, PR bases, heavy runs.
  The *decisions* were not its own.
- **Cost of the dynamic traffic.** The recipient turns, until each went quiet or 60 min passed,
  came to about 933 turns and 189 M tokens, about **$129** at proxy list prices. This is an upper
  bound, since it includes the useful work each message started. The stack-driver resumes are the
  most expensive single items: 2 to 9 M tokens each, mostly cache reads.
- **Recommendation.** Do not keep a long-lived LLM orchestrator or conductor. Keep the main
  session as the only judge across CRs ("Chief of Staff"), and wake it on events (`crf watch` under
  Monitor). Make all steering **state-driven**, with a few `crf` commands the sketch lacks: `note`,
  `hold`/`release`, `cancel`, `add --top/--after`, `order`, `grant`, `pause`/`resume`, `slots`,
  `ci rerun`. For unattended nights, add a **stateless, event-triggered judge**: a fresh small LLM
  with a policy card, around 50 to 100 k tokens per event. The only real loss is
  **interrupting a coder mid-round while it keeps its warm context** (3 to 5 cases in 10 days). See
  §7.

## 1. Data and method

| Source | Content |
| --- | --- |
| `~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-….jsonl` (239 MB) and `…/subagents/` (1,139 agents with meta) | main session and every factory agent |
| `…/521459c8-bb7f-489f-ad0a-3f6e3c36685c.jsonl` | the only other session in the window with SendMessage (7, okf-schema workers) |
| `markdown-okf-schema-studio/.agents/changes/03-requests/` and `04-archives/` | RUN-BRIEF, addendum run 5, STATE, TASKS, STACK-STATE, P1-RUN-BRIEF |

How it was measured, with the scripts in [scripts/](scripts/):

- `scan.py` and `sends2.py` list every SendMessage and Agent call, deduplicated by tool-use id,
  and resolve each recipient through `agent-<to>.jsonl` and its `.meta.json`.
- `effects.py` finds the delivery in the recipient's transcript. The delivery is an
  `attachment.queued_command` while the agent runs, or a user turn
  `Another Claude session sent a message: <agent-message …>` when it is resumed. The script then
  records latency, the actions that follow, and the turns and tokens until the next delivered
  message or 60 min. Messages delivered in the same batch count their cost once.
- `classify.py` applies keyword rules, then manual overrides for all 103 main-session messages and
  for every relay between agents (`overrides.json`). `stats.py` aggregates.
- Cost is an **estimate** from proxy list prices per million tokens. Sonnet: input $3, cache read
  $0.30, cache write $3.75, output $15. Opus: $5, $0.50, $6.25, $25. The exact 5.5-generation
  prices were not checked.
- The "user-triggered" label is a heuristic: a user message less than 15 min before the send.
  Under it, 85 of 103 main → factory messages follow a user message and 18 are the main session's
  own supervision.

Data files: `sends.tsv`, `fac.tsv`, `nonfac.tsv`, `usermsgs.tsv`, `main_rows.txt`,
`agent_rows.txt`, `stats.json`, `facrows.pkl`.

## 2. How messages actually reached running agents

| Recipient state | Example | Delivery |
| --- | --- | --- |
| Orchestrator blocked in **parallel foreground** `Agent` calls to drivers | "Orchestrator night run", 10-22. The main session diagnosed it at 21:38: "blocked since 22:55 because your four driver Agent calls are waiting for all four drivers to return" | 88 and 117 min |
| Orchestrator **parked** after launching background drivers (turn ended, waiting for a child) | Orchestrator D, 10-23 20:50. "User: focus 056, Opus allowed" was sent at 21:21 and **delivered at 05:27** (8 h 05 min), together with "max 8 commits" | when the next child returns |
| Same, many messages piling up | Orchestrator B: 8 messages delivered **together at 18:21:43**, 46 to 185 min late. It then found "All of 044–047 are landed already", because the main session had done the work | one batch |
| Orchestrator killed or interrupted before it read anything | "Orchestrate CRs 024/025/026" (3 messages) and "Orchestrator: CRs 024-029" (6), 10-22 | never; TaskStop, then a new brief |
| Agent **finished**, then SendMessage **resumes** it | P1 stack orchestrator on the night of 10-27: 7 resumes in 0 to 8 s. CR 060 driver: 0 to 3 min | immediate |
| Driver in an active tool loop | CR 045 driver, scope change (#77): 155 s, then coder round 2 starts | minutes |
| Run 5 orchestrator, live now | `a725410…` started 6 foreground Agents at 20:09. "Overnight goal" (20:58) and "New CR 148" (21:19) were **still not delivered at 21:54Z** | pending (the same failure as 10-22) |

So the "message the orchestrator, it acts at its next tick" model (sketch §13, row 2) held only
when the orchestrator was idle-and-finished (then resume) or actively looping in the foreground.
That is 35 of 89 deliveries under 5 min. Parallel fan-out, the factory's purpose, is exactly the
state where messages stall. The main session adapted. It messaged drivers directly (14 times, 0
lost). It did merges and rebases itself, for example #89: "I rebased PR #42 (047) on 7149d6d
myself… Tell the 047 driver: do not push". It killed and re-briefed orchestrators ("Previous
orchestrators froze (they never wrote their status file and stopped reading messages)", Agent
call at 10-22 20:53). Two orchestrator relays also failed on guessed names
(`cr-047-driver`, `cr048-driver`: "No agent named … is reachable"). One main message about CR 045
went to the CR 046 driver by mistake, and that driver ignored it.

## 3. Counts per category (factory set, window 10-17 → 10-27)

`M` = sent by the main session, `a` = relayed by an orchestrator. Latency = send → delivery. The
cost column covers the recipient's turns until it went quiet or 60 min passed (upper bound).

| Category | n (M/a) | delivered | median latency | >30 min | turns | tokens | ≈ cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A Information request / FYI | 8 (8/0) | 8 | 54 s | 0 | 113 | 10.9 M | $7 |
| B Add / remove / reprioritise CR or task | 15 (15/0) | 9 | 41 min | 5 | 29 | 2.2 M | $3 |
| C Change the scope or content of a CR in flight | 19 (16/3) | 17 | 3 min | 3 | 154 | 32.5 M | $24 |
| C2 Grant extra rounds | 9 (6/3) | 7 | 1 s | 1 | 33 | 3.4 M | $4 |
| D1 Merge happened → land, rebase, prune | 21 (18/3) | 17 | 3 min | 6 | 149 | 28.5 M | $21 |
| D2 Stack shape (add or append, reorder, top, cycle repair, restack after a fix) | 11 (4/7) | 11 | 8 s | 1 | 163 | 43.6 M | $20 |
| E "I need the machine", pause, keep awake | 3 (3/0) | 3 | 46 min | 2 | 11 | 1.0 M | $2 |
| F Unblocking (permission, authorisation, locked screen) | 4 (1/3) | 4 | 3 s | 0 | 11 | 0.7 M | $1 |
| G Restart or nudge after a stall or rate limit | 11 (5/6) | 10 | 2 s | 1 | 69 | 14.2 M | $13 |
| H CI or infra decision (bisect, rerun after a hang, regression fix, stress advisory) | 5 (4/1) | 5 | 0 s | 0 | 63 | 20.6 M | $12 |
| I Process or rule change mid-run (English, trailer, branch prefix, PR template, ready not draft, folder layout) | 19 (19/0) | 15 | 8 min | 3 | 127 | 30.8 M | $22 |
| M Ownership or coordination (stand down, "I pushed r4 myself", "047/048 belong to B") | 5 (4/1) | 5 | 2 s | 1 | 11 | 1.1 M | $2 |
| **Dynamic subtotal** | **130 (103/27)** | 111 | | 23 | 933 | 189 M | **$129** |
| K Round dispatch (orchestrator → coder or analyst) | 64 | 64 | 1 s | 0 | 538 | 141 M | $95 |
| L Report back (worker → orchestrator or main) | 38 | 35 | 82 s | 0 | 278 | 84 M | $58 |

Outside the factory, the same window holds 51 more sends. About 33 are round dispatch while the
main session itself acted as orchestrator (T38–T45, P3–P11, CR 024/025, before 10-22 16:00).
8 resume an agent after a rate limit. The rest: 3 status pings and replies (one to a
depth-3 coder, skipping its driver), 4 scope changes (refactoring study, CR 043 re-scope), and 2
rules (PR for an external reader, commit trailer). Session `521459c8` adds 7 more, all to plain
workers and all applied within 1 to 42 s: 2 process enforcements, 1 "redo as strict copy", and
4 scope flips in 8 min (include, revert, two decisions on PR #51).

Restarts and re-briefs through Agent:
- 10-22 17:21 rate limit
- 19:42 after a kill
- 20:25 stuck
- 20:53 froze
- 10-23 07:25 process change: the rebase orchestrator was replaced by a stacked-PR one
- 09:27 after a kill
- 10-24 15:05 F2 resumed after the pause
- 19:34 J replaced I
- 10-27 10:10 the main session spawns "Driver CR 123 round 6" itself
- 19:14 restart after an API error

TaskStop on factory agents: 7 orchestrators and 2 drivers, all on 10-22 and 10-23.

## 4. Ten most significant examples

| # | When (UTC) | Path | Quote (trimmed) | What happened | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | 10-22 19:19–20:24 | main → orchestrators 024/025/026 and 024-029 (9 msgs) | "New CR for you: start a CR driver for CR 028 now…", "User grants CR 025 two more rounds" | **None delivered**. Both orchestrators were killed (TaskStop 19:38, 20:24) and re-briefed. The user, at 20:10: "J'ai l'impression que ce fonctionnement avec sous agent orchestrateur et driver pose des soucis" | `agent-acb1ffde82208b8a6.jsonl`, `agent-a5ce448bcd150ecf4.jsonl` (last record "[Request interrupted…]"); main TaskStop |
| 2 | 10-23 14:24–15:58 | main → orch 044-046 and orch B (15 msgs) vs main → CR 045 driver | "CR 045: user adds file includes, round 2", "PR 41 merged: rebase all, land 046" | Orchestrators received them in batches 50 to 185 min late. The **direct driver message took 155 s** and the driver started coder round 2. The main session merged, rebased and landed itself in the meantime | `agent-a92d9f325a79ccb3a` 15:42:20, `agent-a27906e9e122c40d7` 18:21:43, `agent-aaaf1a3073737e9cb` |
| 3 | 10-23 21:21 → 05:27 | main → Orchestrator D | "User update: the refactor (056) has priority tonight. Opus is allowed everywhere…" | Delivered **8 h 05 min** later, when the background driver returned. The orchestrator handed back in 3 turns | `agent-ae6a4b32799330dfa.jsonl` |
| 4 | 10-24 06:34 | user → main → Orchestrator F | "PAUSE NOW. The user has to shut everything down… Stop without losing data" | Delivered in 310 s. All four analysts had finished; STATE updated; handed back. Resumed 9 h later by a **new** orchestrator F2 from files | `agent-af1be46b47fd4a981`, F2 `agent-a1005e97f0059f63e` |
| 5 | 10-25 21:01–22:38 | user → main → P1+P2 orch → coder CR 084 (same coder resumed 5 times) | "{list-table} must also get row handles", "handles outside the table", "wide, horizontally scrolling table" | Three design changes from the user's screenshots, each relayed in 1 to 5 min to the **same coder**, which kept its knowledge of the code. Scope grew inside one PR | `agent-aa284441fb21ed442`; coder `agent-abf91f7ea342896ed` |
| 6 | 10-25 16:13 → 10-26 05:05 | main → P1+P2 stacked orchestrator (12 msgs, median 2 min) | "Rebase stack: PR #91 merged", "Night batch: dollarmath + 15 P3 CRs", "Fix goes on top; leave branch names" | The **stack was built incrementally**: #64–#87 (merged by the user, then pruned), then #88–#108, then the fix as a new top #109, with heavy CI green at 05:05 | `agent-aa284441fb21ed442` hand-backs 03:43 and 05:05 |
| 7 | 10-27 00:33–06:24 | main (autonomous at night) → P1 orch (resumed, 0 to 8 s) → stack driver (resumed 7 times) | "Decision (guideline: a red PR goes to the top): Reorder the stack to 107…120, 124, 123", then "PR bases now form a cycle" | Rounds 4 to 5 granted for 113, 123 and 115. The main session bisected with 3 parallel heavy runs (04:05). Reorder, then cycle repair. Final: "Stack #131 (107..120, 124 #130, 123 #128). Heavy CI on top … SUCCESS". Each stack-driver resume cost 2 to 9 M tokens | main 23:30–05:23; `agent-a7dc8322f1d2b1eb9`, `agent-a05ca1697b4543086`; `04-archives/STACK-STATE-2026-10-26.md` |
| 8 | 10-26 22:37 / 22:49 | main → P1 stack orchestrator | "Add CRs 122-124 to the stack… New stack order in P1-RUN-BRIEF.md", "CR 121 is dropped: the user fixed it themselves" | The **main session edited the stack order in the brief** and archived 121 itself. The orchestrator received both 52 and 41 min late, then handed back | `04-archives/P1-RUN-BRIEF-2026-10-26.md` "Stack order (bottom → top, fixed)"; `agent-a7dc8322f1d2b1eb9` |
| 9 | 10-27 17:45 → now | main → run 3 orch → run 5 orch (restart) | "Add CRs 137–147 on the CR 135 stack", "New CR 148 on top of the stack" | The addendum, written by the main session, sets the bases by file overlap (140 → 141 → 142, 143 → 144, 145 → 146). The orchestrator applied them ("built ON TOP of CR 140 (same files)") and added cross-CR constraints ("must keep CR 135's hardened sanitizer guarantees"). The orchestrator died on an API error (19:14 restart). #282 and #283 were still queued at 21:54Z | `RUN-BRIEF-addendum-run5.md`; `agent-a21e1ec0a8fc37d31`, `agent-a725410a2169211f8` |
| 10 | 10-23 12:42–12:53 | user → main → CR 041 driver (direct, 4 min) | User: "c'est trop long il faut passer à la vitesse supérieur… Tu peux committer et tester la MR ?" → main: "PR #35 head is now 9d2e885 = 9243cf5 (your r4 WIP) + ci: make the stress job advisory" | The **main session took over the branch**. The driver adopted the new head without resetting it, ran reviewer r4, watched CI and set ready, all in 6 min | `agent-afbf80cc903eb7766`; main #65–#67 |

## 5. "A driver built the stack dynamically": the cases

1. **P1+P2 stacked orchestrator** (`aa284441…`, 10-25 16:13 → 10-26 05:05, 5.8 MB). It worked
   as driver and stack builder: one coder and one reviewer per CR, each new branch cut from the
   previous CR branch, `gh stack` throughout. It changed shape six times along the way:
   - #70 merged (restack)
   - the user merged #64–#87 (`gh stack sync --prune`, continue)
   - #91 and #93 merged (restack)
   - branch-prefix rename
   - the README CR kept off the stack (user, 16:21)
   - "Fix real-input integration regression" turned into a new top PR #109

   Messages arrived in 0.5 to 21 min because it worked serially in the foreground.
2. **P1 stack driver** (`a05ca169…`, 10-26 21:43 → 10-27 06:24, 4.2 MB, resumed 7 times through
   SendMessage). It appended 123 and 124, absorbed round-4 and round-5 fix commits for 113, 115
   and 123, reran heavy CI, reordered 124 below 123, then repaired the base cycle that its own
   reorder had left. The *order* came from the main session, through the orchestrator.
3. **Run 2 stack drivers** (`aafaf178…`, `ab5a5554…`, 10-27): 7 PRs #132–#138 as gh stack #139,
   then a restack after #128 merged and the `just requirements-update` authorisation.
4. **Run 5** (now): bases chosen by file overlap, planned by the main session in the addendum and
   applied by the orchestrator in the driver prompts.

**Who held the context.** The *why* lived in the main session and in files: why 141 sits on 140,
why 123 goes to the top, why 121 was dropped, why CR 059 became one PR. That includes
`00-request.md` decisions, the briefs, P1-RUN-BRIEF and the addendum. The LLM stack executors
held *execution* context: current SHAs, PR bases, which heavy run is which. Code can hold that
better, as the base cycle shows. Coders held *code* context, which mattered in example 5 (084) and
in CR 041 (example 10). No case was found where an orchestrator or a driver knew something the
user's flexibility depended on that was not also written in a file or in the main session.

## 6. Judgment per category against the sketch

Legend: (a) the workflow handles it as is; (b) the Chief of Staff runs a `crf` command; (c) needs
an LLM that is reachable and holds context; (d) lost.

| Category | Verdict | Why, and what is missing in the sketch |
| --- | --- | --- |
| A Info | **b** | `crf status` and `crf render`. A "why did it fail" narrative needs the coder's hand-over note and the reviewer's verdict, both in state. Add `crf status --notes <cr>` |
| B Add / remove / reprioritise | **b** | `crf add`, `crf cancel`, `crf hold` are in §13. **Missing**: `crf order`/`priority` ("focus 056 only", "fix PR 15/16 now"), `crf slots N` ("raise new-CR driver slots"). The effect comes at the next step boundary, which beats today's 41-min median |
| C Scope in flight | **b**, partly **d** | Decision in `00-request.md` plus `crf note <cr>`, read by the next round. **Loss**: a coder mid-round cannot be redirected with its warm context (084 three times, 045 round 2, 041). Cost: one wasted or extra round. Option: `crf note --now` cancels the running round and restarts it with the note (open question: can a workflow cancel one agent?) |
| C2 Round grants | **b** | §3.3 says "only the user grants more", but no command exists. **Add** `crf grant <cr> rounds=N` (9 cases, 3 of them decided at night by the main session) |
| D1 Merge → land / rebase | **a** | `crf status --merged` `/loop`, then `crf stack`, then `crf-land`. Pure mechanics. Today it took 21 messages and many main-session turns |
| D2 Stack shape | **b** + **a** | Requires the **stack order in state** (`crf stack order 107..120,124,123`, `crf add --top`, `crf cancel` drops from the chain). After that, `crf stack` rebuilds it deterministically; an LLM is needed only for rebase conflicts. The sketch's `crf stack` lacks order editing and base-cycle checks. Saves 2 to 9 M tokens per restack |
| E Machine or pause | **b** | `crf pause --all` stops at step boundaries; relaunch resumes (§3.6). Keeping the machine awake (caffeinate) and the WINDOW-TESTS lock belong in `crf`, not in prompts. "Release the lock now" needs `crf lock release`; no such case was seen |
| F Unblock | **a** / **b** | The denial is recorded with the exact command (§3.3). A new authorisation (`just requirements-update`) goes into rules or settings, read by the next round's agents. A locked screen (CR 123) is a `blocked` CR |
| G Restart / stall | **a** | No LLM orchestrator left to stall; relaunch resumes. This removes all 9 kills, about 10 re-briefs, 11 nudges and the 8 resumes after rate limits outside the factory |
| H CI or infra | **a** + **b**/**c** | One rerun on infra failure is mechanical (a). Bisecting across the stack, "make stress advisory" and "regression fix as a new top PR" need judgment across CRs. In the data, **the main session made all of these**. The Chief of Staff applies them with `crf ci rerun`, `crf add --top` and `crf note` |
| I Process rule | **b** | Edit the guideline or rules plus `crf note --all`. Rules that touch already-open PRs need `crf ship --update-body` |
| M Ownership | **a** / **b** | One workflow owns all CRs, so there is no "stand down" and no "belongs to B". When the user or the main session takes a branch ("I pushed r4 myself", "I rebased #42 myself"), it needs **`crf hold <cr>` / `crf release <cr>`** so the workflow does not overwrite the branch |
| K / L | **a** | Workflow steps and the state or event log |

Truly lost: **mid-round redirection of a live coder with its context kept** (C, about 3 to 5
cases), and **free-form questions to a driver** (A, 2 status pings, mitigated by notes). There
is also the behaviour the sketch already names in §13: a driver LLM **improvising on surprises**
(the shared node_modules drift in T1, the locked screen, the self-made base cycle). These become
`blocked` CRs and wake the main session.

## 7. Recommendation: minimal LLM presence

1. **No long-lived orchestrator and no sleeping conductor by default.** In practice the
   orchestrator relayed and executed main-session decisions. Its most reliable mode was
   "hand back at a decision point, get resumed by message": the P1 night, 7 resumes in 0 to 8 s,
   100 to 400 k tokens each. That is exactly "blocked CR, then `crf watch` wakes the main session,
   then a `crf` command". The main session already played the judge every time.
2. **Make the steering surface state-driven** and picked up at each step boundary. Add `crf note
   [--all|--now]`, `hold`/`release`, `cancel`, `add --top|--after`, `order`, `grant`, `slots`,
   `pause`/`resume`, `ci rerun`, `stack order`, and `status --notes`. Every command writes an event
   with a reason (§13, last row). This keeps the "why" that today lives only in transcripts.
3. **Keep three LLMs, all short-lived**: the coder and the reviewer per round, and the **conflict
   fixer** for `crf stack`. Hand-over notes carry the coder's context between rounds. Measure the
   cost of losing the warm coder on the cases from example 5.
4. **Unattended nights.** On the night of 10-26/27, 6 decisions came between 23:30 and 05:23:
   round grants, rerun after a hang, reorder, bisect, Opus coder. Without an LLM they would have
   waited until 06:20. Use an **event-triggered stateless judge**: a fresh agent that reads
   `crf status --explain <cr>`, the events and a policy card ("red PR to the top; at most +1
   round; bisect before regranting"), then applies `crf` commands. Its cost is about 50 to 100 k
   tokens per event, roughly $0.1 to $0.3 at Sonnet prices. A long-lived conductor rereads 150 to
   400 k tokens per wake and needs the same policy anyway.
5. **Optional, only if measured worthwhile: a per-CR "warm coder" mode** that stays alive across
   rounds and receives `crf note --now` by message. This is the only place where a reachable LLM
   with context showed value. Keep it opt-in per CR, for UI work driven by screenshots.

Cost implication (inferred). Recipients of D1, D2, G and M cost about $55 of the $129 dynamic
total; that mostly goes to code. C, C2, I and B cost about $52 and become cheap next-round prompt
additions. The main session's own turns for composing messages stay about the same, as one short
`crf` command each instead of a 600-character message. Removing the 9 kills, about 10 re-briefs
and the batches that arrived hours late is the larger gain, in latency rather than dollars.

## 8. Caveats

- Effect windows end at the next delivered message or after 60 min. For long-running recipients
  they include work the message only unblocked, so costs are upper bounds.
- Proxy prices; tokens are exact as read from `message.usage`, deduplicated by message id.
- Categories rest on manual reading of all 103 main messages and the relays; the user-trigger
  attribution is heuristic.
- Run 5 is live. The "pending" status of messages #282 and #283 was observed at 21:54Z and may
  have changed since.
