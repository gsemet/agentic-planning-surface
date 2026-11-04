# User journey

Realigned 2026-10-23 on the user's own description (round 25 in
[02-user-answers.md](../02-user-answers.md)). The previous, detailed version was judged too
complicated and is replaced by this one.

## Journey

| # | Moment | The user | The agent / the surface | Delay |
| --- | --- | --- | --- | --- |
| 1 | Join | clones the team's planning surface, opens it in VS Code | loads `AGENTS.md`, which points to the skills ("guidelines") | — |
| 2 | Pick a project | "I want to work on AAA" | the skill triggers, presents AAA's inbox and backlog | — |
| 3 | Browse | reads the ideas in VS Code or in the Markdown Studio | — | — |
| 4 | Capture | "here is an idea: YYYY" | creates the idea folder in the inbox (or the backlog) | synced ≤ 30 s |
| 5 | Triage | the PO sees it, accepts it into the backlog (small team: the dev is the PO) | — | others see it ≤ 1 min |
| 6 | Shape | anyone grills the idea, builds prototypes | writes the grill and prototype files | others see it ≤ 1 min |
| 7 | Accept as CR | the PO edits the idea's YAML; the git commit says who | — | ≤ 1 min |
| 8 | Technical grill | the builder starts | dedicated checkout of AAA in `.worktrees/`; a separate session there loads AAA's `AGENTS.md` and gets the CR folder path (G92) | — |
| 9 | Spec + code | the builder runs their workflow (native, spec-kit, OpenSpec) | spec often committed in AAA, PR opened on AAA | — |
| 10 | Archive | the PR on AAA is merged | the CR is archived in the surface | — |

## Gaps

Answered in round 26 (G90–G96) and folded into [03-change-spec.md](../03-change-spec.md):
1 → agent sessions only; 2 → push ≤ 30 s, pull ≈ 30 s; 3 → the builder volunteers; 4 → folders +
YAML; 5 → two grills; 6 → the agent merges; 7 → separate session; 9 → `.worktrees/`;
10 → links + spec copy; 11 → the builder. Gap 8 stays open (spec §11).

1. **Who syncs when no agent runs.** "≤ 30 s / ≤ 1 min for everyone" needs a process running on
   every machine, including the PO's when they only browse in VS Code. Started by the skill (G82),
   it only runs while an agent session is open. Options: a small user service, a VS Code task or
   extension, or the Studio (G61 says independent).
2. **Timings change**: G37 said commit after 30 s, push every 2 min. The new target is push within
   30 s and pull about every 30 s, so a change reaches everyone within 1 min.
3. **Two acceptances**: the PO accepts an *idea* into the backlog (step 5), then accepts it as a
   *CR* by editing the YAML (step 7). Is step 7 also the assignment of the builder (`owner`)?
4. **State in the YAML or in the path**: step 7 is a YAML edit, while G18 / G24 put the state in
   the folder (`01-inbox` … `05-trash`). Keep both (folder for the big stages, YAML for accepted
   and builder), or move everything to the YAML and let views group the ideas?
5. **Grill before acceptance**: step 6 allows grilling in the backlog by anyone, which reverses
   G58 (grill after take only). Two grills now: a product grill in the backlog, a technical grill
   by the builder.
6. **Several people on one idea**: step 6 is collaborative, so simultaneous edits of the same file
   become normal, not rare (G7). The conflict copy (G38) will show up more often.
7. **Sub-agents and the target's `AGENTS.md`** (step 8): an agent's sub-agents usually keep the
   parent's instructions; loading another project's `AGENTS.md` depends on the agent tool. The
   reliable path is a separate session started in the checkout; otherwise the trigger must tell
   the sub-agent to read AAA's `AGENTS.md` first.
8. **Agent-neutral `AGENTS.md`**: some agents read `CLAUDE.md` or their own file, not `AGENTS.md`;
   the surface may need thin pointer files.
9. **Where the dedicated checkout lives** (step 8): under the surface (`projects/AAA/.worktrees/`,
   G44) or anywhere the builder wants.
10. **The spec lives in AAA** (step 9): the CR folder in the surface keeps the intent, grills and
    prototypes; it should link to the spec and the PR in AAA, so the archive stays complete.
11. **Who archives** (step 10): the builder tells the surface (G51), or something notices the
    merge.
