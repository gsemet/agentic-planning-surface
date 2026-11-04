# Autosync interview responses

Source: [01-intent.md](./01-intent.md). Interview date: 2026-11-04.

The answers below record the user's choices. Recommendations that were not selected are not
decisions. Q8 stopped the interview temporarily; the user then explicitly asked to continue.
Q43 was answered "best guess" together with a request to discuss deployment and open-source
alternatives; the interview continued. Q58 stopped the interview with a request to use best guesses,
write the document, and present the open-source alternatives.

## Initial scope and safety

| Question | Answer |
|---|---|
| Q1: What should autosync synchronize? | The planning-surface repository only. Q46 later clarified that the CLI itself should be reusable in other explicitly initialized repositories. |
| Q2: What outcome should autosync guarantee when edits conflict? | Safe automatic merge; preserve conflicts for human resolution. Q11 and Q14 later revised this to agent-first resolution with human escalation. |
| Q3: How should users experience synchronization? | Ideally, root `AGENTS.md` strongly guides an agent to use the autosync tool in the background. |
| Q4: What matters most when connectivity or the remote is unavailable? | Keep editing locally and sync when connected. |
| Q5: Should the existing agent-session-only design remain the baseline? | Yes. |
| Q6: Which local changes may autosync commit? | All eligible repository changes. |
| Q7: What synchronization delay should be the initial target? | Configurable, with a 30-second default. Q19 and Q24 refined the timing. |
| Q8: Would you like me to stop the interview here? | Yes. After the summary, the user asked to continue. |

## Eligibility, conflicts, and concurrency

| Question | Answer |
|---|---|
| Q10: Which file states should be eligible for automatic commits? | Tracked changes and new non-ignored files. |
| Q11: What may an agent do with an ambiguous conflict? | The background process notifies the agent to resolve the conflict; the agent notifies the user only when it cannot. |
| Q12: How should autosync treat changes already present when it starts? | Include eligible existing changes and show them. |
| Q13: Would you like me to stop the interview here? | No. |
| Q14: May the agent resolve and apply conflicts without prior human approval? | Yes, when confident; escalate otherwise. |
| Q15: How should autosync guard against accidentally publishing sensitive files? | Block detected secrets and report affected files, subject to the user-approval policy in Q20 and Q25. |
| Q16: How should simultaneous agent sessions coordinate autosync? | One coordinated process per checkout. |
| Q17: What should autosync do when another Git operation is already in progress? | Pause, report, and resume afterward. |
| Q18: Would you like me to stop the interview here? | No. |

## Timing, LFS, and notifications

| Question | Answer |
|---|---|
| Q19: How should the 30-second delay behave during continuous editing? | A quiet period plus a maximum interval. |
| Q20: What should happen when a secret is detected? | Ask the user whether to proceed. |
| Q21: What should happen if Git LFS is needed but unavailable? | Be transparent and follow Git LFS configuration. Q26 and Q29 clarified failure behavior. |
| Q22: Which agent should receive a conflict notification? | One assigned active agent; otherwise notify the user. |
| Q23: Would you like me to stop the interview here? | No. |
| Q24: What should the default timing values mean? | A 10-second quiet period and a 30-second maximum, both configurable. |
| Q25: May user approval override a detected-secret warning? | Yes, with explicit per-incident approval. |
| Q26: What should happen if configured Git LFS cannot complete its work? | Continue and report partial synchronization, subject to the boundary clarified in Q29. |
| Q27: Which branch should autosync synchronize? | The current branch and its configured upstream. |
| Q28: Would you like me to stop the interview here? | No. |
| Q29: What may continue when an LFS operation fails? | Continue local commits and fetching; withhold affected pushes. |
| Q30: What should happen when the current branch has no configured upstream? | Ask the user to configure or choose an upstream. |
| Q31: How should users and agents see sync problems? | Persistent status and active notifications. |
| Q32: How should autosync handle files that change during synchronization? | Preserve them for the next cycle; pause if unsafe. |
| Q33: Would you like me to stop the interview here? | No. |

## History, recovery, and staging

| Question | Answer |
|---|---|
| Q34: How should local and remote histories be combined? | Rebase unpublished commits; never force-push. |
| Q35: How should autosync retry recoverable failures? | Retry transient failures with bounded backoff; notify on actionable errors. |
| Q36: What should happen when the last agent session ends with pending changes? | Attempt a bounded final sync and report pending work. |
| Q37: Where should sync status be available? | Command-readable status and human-readable actionable status. |
| Q38: Would you like me to stop the interview here? | No. |
| Q39: What must be preserved when a conflict cannot be resolved? | Both sides, their history, and uncommitted local edits. |
| Q40: May people and agents keep editing while a conflict awaits resolution? | Allow safe local editing; pause affected synchronization. |
| Q41: How should autosync handle an existing Git staging area? | Preserve staging state and ask before including it. |
| Q42: What should secret detection cover before a push? | All content newly introduced by the pending push. |
| Q43: Would you like me to stop the interview here? | "best guess. i want to talk about the deployment like `ai-autosync-git init .` will patch the AGENT.md and start the background task (`ai-autosync-git start`). and you will do a market analysis to find similar opensource project" |

## Deployment and reuse

| Question | Answer |
|---|---|
| Q44: How long should the background task started by init run? | Start immediately and stop when the last agent session ends. Q49 clarified the case where no session is active. |
| Q45: Which agent guidance file should init update? | Root `AGENTS.md`. |
| Q46: Is the CLI intended to work beyond this planning surface? | Reusable for explicitly initialized Git repositories. |
| Q47: How should existing open-source projects influence the product? | Evaluate reuse or adaptation before building missing behavior. |
| Q48: Would you like me to stop the interview here? | No. |
| Q49: What should init do if no agent session is active? | Configure and wait for an agent session. |
| Q50: How should the tool learn that an agent session is active? | `AGENTS.md` is standard; expect all agents to follow it. Q55 specifies registration and release. |
| Q51: How should init update an existing AGENTS.md? | `AGENTS.md` shall point to `.agents/guidelines/autosync.guidelines.md`. |
| Q52: What should repeated init do to an already initialized repository? | Preserve settings and avoid duplicate tasks. |
| Q53: Would you like me to stop the interview here? | No. |
| Q54: How should users install the CLI? | Run on demand with `uvx`. |
| Q55: How should an agent signal the end of its session? | Register on start; release on exit; recover stale registrations. |
| Q56: How should init maintain the linked autosync guidance document? | Create it if absent; preserve and report differences. |
| Q57: Where should autosync configuration live? | Version shared settings; keep machine settings and runtime state local. |
| Q58: Would you like me to stop the interview here? | "stop here. best guess, write the doc and present me the other opensource solution" |
| Q59: Which handoff option do you prefer? | "capture change aside of the intent file" |

Q9 was the first, interrupted handoff prompt; no handoff was selected before the interview resumed.
