# Agent-aware Git autosync: change specification

**Status:** Interview handoff; not approved for implementation.  
**Source:** [Intent](./01-intent.md) and [interview responses](./02-interview-responses.md).

## Intent

Provide an automatic, Git-backed synchronization experience for a shared planning surface. People
and agents can continue editing locally when offline, while eligible changes are committed and
synchronized during agent sessions. Conflicts are resolved safely where possible and escalated when
an agent cannot resolve them confidently. Preserving work takes precedence over appearing synced.

The initial deployment is the planning-surface repository. The CLI should also be reusable in
other Git repositories when explicitly initialized there; it must not automatically synchronize
associated code repositories.

## User experience and deployment

- Run the CLI on demand through `uvx`. The discussed command interface includes
  `ai-autosync-git init .` and `ai-autosync-git start`; exact invocation and package name remain
  to be confirmed.
- Initialization configures the selected repository and creates or updates root `AGENTS.md` so it
  points to `.agents/guidelines/autosync.guidelines.md`. Preserve existing guidance.
- Create the linked guidance document if absent. If it already exists and differs from the intended
  guidance, preserve it and report the difference rather than silently overwrite it.
- If an agent session is active, initialization starts synchronization. Otherwise it configures
  the repository and waits for an agent session.
- Agents are expected to follow the guidance: register when starting, release when exiting, and
  allow stale registrations to be recovered after unexpected exits.
- Coordinate at most one sync process per checkout, even when multiple agents are active.
- When the last participating agent session ends, attempt a bounded final sync, preserve remaining
  local work, report anything pending, and stop.
- Reinitialization preserves existing settings and does not create duplicate tasks.
- Version shared repository settings; keep machine-specific settings and runtime state local.

The user expects agents to follow `AGENTS.md`; compliance by all agent hosts is an assumption, not a
verified guarantee.

## Synchronization behavior

- Include eligible changes to tracked files and new non-ignored files, including changes already
  present when autosync begins. Make their inclusion visible.
- Preserve a user's existing staging state and ask before including staged work in an automatic
  commit.
- Use a configurable quiet period and maximum interval, initially 10 seconds and 30 seconds
  respectively, so continued editing does not postpone synchronization indefinitely.
- Synchronize the checkout's current branch with its configured upstream. If none is configured,
  ask the user to configure or choose one rather than guessing.
- Rebase unpublished local commits onto the upstream when needed. Never automatically force-push or
  rewrite published history.
- Pause, report, and resume around another in-progress Git operation.
- Preserve edits made during synchronization for a subsequent cycle. Pause and report if their
  preservation cannot be guaranteed.
- Continue local editing during an outage and synchronize when connectivity returns. Retry transient
  failures with bounded backoff; report authentication and configuration problems requiring action.
- Offer persistent, actionable, human-readable and command-readable status, and actively notify
  the responsible agent or user when intervention is required.

## Conflicts and preservation

- Merge automatically when safe. Notify one assigned active agent when a conflict needs resolution;
  notify the user if no agent can take responsibility.
- The agent may apply a resolution without prior human approval when confident. Otherwise it must
  preserve the conflict and escalate to the user.
- Preserve both conflicting sides, their history, and uncommitted local edits, including when a
  conflict cannot be resolved or an operation is interrupted.
- Allow further local editing when it can be preserved safely; keep affected synchronization paused
  until resolution.

What establishes confidence, how notification and assignment work, and the precise preservation and
recovery mechanism are unresolved. The words “data-loss-free” express the desired outcome, not a
proven guarantee.

## Secrets and Git LFS

- Detect secrets in all content newly introduced by a pending push, not only the current working
  tree. Report affected files and ask the user whether to proceed.
- A user may explicitly override a warning for the particular incident. Scanner behavior, failure
  handling, and the exact scope of approval remain unresolved.
- Follow the repository's Git LFS configuration. If an LFS operation fails, report partial
  synchronization; safe local commits and fetching may continue, but withhold affected pushes until
  required LFS content is available.
- Do not report a partially synchronized repository as fully synchronized.

## Open-source landscape

See the [detailed assessment](./04-open-source-assessment.md) for a requirement-by-requirement
comparison, pinned source evidence, and reuse risks.

The following is a targeted scan of project documentation, not a hands-on assessment or an
exhaustive market survey. No candidate has been verified against this specification.

| Project | Published capabilities relevant here | Principal qualification |
|---|---|---|
| [GitHub AutoSync](https://github.com/yaseenarshad/github-autosync) | MIT desktop application; watches selected folders, syncs through GitHub, preserves conflicting versions, and provides an AI-resolution prompt. | Its documented handoff is a copied prompt rather than automatic agent notification. |
| [obsidian-sync](https://github.com/alex-furrier/obsidian-sync) | MIT headless daemon and CLI with commits, pull/rebase, status, and a lock against duplicate daemons. | Designed for Obsidian vaults; stops on conflicts for manual resolution. |
| [git-auto-sync](https://github.com/AIZIU/git-auto-sync) | MIT background watcher with automatic commit/push, periodic pull, status, and notifications. | Documents default-branch-only behavior and relies on ignore rules for secrets. |
| [Obsidian Git](https://github.com/Vinzent03/obsidian-git) | MIT Obsidian plugin with scheduled sync and interactive conflict resolution. | Requires Obsidian; agent-driven resolution was not established. |
| [gitwatch](https://github.com/gitwatch/gitwatch) | GPL-3.0 shell watcher with automatic commits and optional pushes. | A narrower watcher; license compatibility and missing capabilities need assessment. |

Evaluate reuse or adaptation before building missing behavior. GitHub AutoSync is a useful reference
for conflict preservation and agent-facing experience; obsidian-sync is a useful headless lifecycle
reference. LFS behavior, secret detection, concurrent edits, agent integration, maintenance, and
license compatibility remain to be verified for any candidate.

## Unresolved decisions and assumptions

The user requested best guesses where the interview stopped. The following remain explicitly
unconfirmed and must not be presented as agreed guarantees:

1. Agent registration, crash recovery, notifications, and behavior when an agent does not follow
   the guidance.
2. Conflict-confidence criteria and safe recovery for binary files, renames, deletions, concurrent
   edits, interruption, and failed resolutions.
3. Secret scanner selection, false positives and negatives, scanning failures, and approval scope.
4. Detached HEAD, protected branches, existing Git hooks, worktrees, external Git races, and the
   behavior while staged changes await approval.
5. Timing semantics for individual fetch, commit, and push operations; retry and final-sync bounds;
   status format; configuration precedence; and upgrade behavior.
6. Exact package and command interface, distribution, supported platforms, and compatibility with
   target agent hosts.
7. Measurable acceptance criteria and validation for preservation, timing, concurrency, Git LFS,
   offline recovery, and multi-user operation.
8. Whether any existing project can be reused without compromising the agreed safety and workflow
   requirements.
