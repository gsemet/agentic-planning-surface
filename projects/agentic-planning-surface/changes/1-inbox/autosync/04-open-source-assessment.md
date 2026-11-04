# Open-source assessment for agent-aware Git autosync

**Assessment date:** 2026-11-04  
**Inputs:** [Intent](./01-intent.md), [interview](./02-interview-responses.md),
and [change specification](./03-specification.md).  
**Purpose:** Determine whether the five previously identified open-source projects can satisfy the
requested behavior as-is, provide an adaptable foundation, or only serve as references.

## Executive decision

**None of the five is established as a safe drop-in solution for the complete specification.**

1. **GitHub AutoSync** is the strongest reference for conflict preservation and concurrent editing.
   Its real-Git test cases, keep-both implementation, and explicit handling of in-progress
   operations make it the most compelling source of ideas and potentially reusable MIT-licensed
   code. However, it is an Electron desktop application, automatically creates a missing upstream,
   includes existing staged files, and filters out large files before considering Git LFS. Its
   conflict policy also publishes separate copies rather than asking an agent to resolve ambiguity.
   A static review identified failure paths that require particular scrutiny before reuse.
2. **obsidian-sync** is the closest Python/CLI-shaped foundation: it has a daemon, status command,
   configurable intervals, and a PID lock. It is not safe to adopt unchanged for this use case:
   it stages everything, uses a configured remote and branch, stops on conflicts, and passes
   `--no-verify` to both commit and push. In particular, bypassing a standard LFS pre-push hook
   can prevent required LFS objects from being uploaded by that hook.
3. **Obsidian Git** is the strongest documented LFS integration and an excellent reference for
   manual conflict UX. It depends on Obsidian and does not provide the requested independent,
   agent-session-scoped CLI.
4. **git-auto-sync** is useful as a watcher and desktop-service reference, but its default-branch
   restriction, staging behavior, timing, and a visible retry gap make it a poor direct foundation.
5. **gitwatch** is a compact watcher and commit/push reference, not a complete collaborative sync
   engine. Its GPL-3.0 license also requires a deliberate compatibility assessment before copying
   or incorporating code.

**Recommendation:** Do not deploy any candidate as-is against the planning surface. Evaluate
selective reuse of GitHub AutoSync's tested conflict concepts and obsidian-sync's CLI/daemon
concepts, subject to licensing and a fresh safety review. Treat the two implementations as
references, not as interchangeable components: they use different languages and runtimes, and no
stable standalone integration API was established in this assessment.

## Scope and evidence standard

This assessment covers the five projects in the existing shortlist, not every open-source project
on the market. It uses their public documentation and a static inspection of the pinned source
revisions below. Source and tests were read, **not executed**. No packages from the candidate
repositories were installed, and no claims of observed runtime behavior or independently proven
data-loss freedom are made.

Labels in the matrix mean:

- **Partial:** some relevant behavior is evidenced, but it does not meet the entire requirement.
- **Mismatch:** inspected source or documentation establishes a meaningful incompatibility.
- **Unknown:** the reviewed material does not establish compliance; this is not proof of absence.

No cell is marked “fully met”: requirements include safety and lifecycle guarantees that the
available static evidence does not establish.

## Revision and project inventory

| Short name | Project and license | Source revision inspected |
|---|---|---|
| **GHA** | [GitHub AutoSync](https://github.com/yaseenarshad/github-autosync), MIT; Electron/TypeScript desktop application | [`ad4118e`](https://github.com/yaseenarshad/github-autosync/tree/ad4118e1f4fd898f1abe99ab6c184955b9171fbf), 2026-10-29 |
| **OS** | [obsidian-sync](https://github.com/alex-furrier/obsidian-sync), MIT; Python CLI and daemon | [`864658b`](https://github.com/alex-furrier/obsidian-sync/tree/864658b39744c760f8f79ca41a7e9ececc4f89d1), 2026-05-15 |
| **GAS** | [git-auto-sync](https://github.com/AIZIU/git-auto-sync), MIT; Python script and OS services | [`5e8c829`](https://github.com/AIZIU/git-auto-sync/tree/5e8c829a18e243f0f8586ee06e16923bf8859376), 2026-05-07 |
| **OG** | [Obsidian Git](https://github.com/Vinzent03/obsidian-git), MIT; Obsidian TypeScript plugin | [`4ede23c`](https://github.com/Vinzent03/obsidian-git/tree/4ede23cc4bbe3b7ee3fdc4b7a04e02583b690531), 2026-11-03 |
| **GW** | [gitwatch](https://github.com/gitwatch/gitwatch), GPL-3.0; Bash watcher | [`04735cf`](https://github.com/gitwatch/gitwatch/tree/04735cfa8973a5ba425ec4befb25ecb04074465c), 2026-08-13 |

Revision dates are commit dates, not a determination of project maturity or maintenance quality.

## Requirements comparison

The cells summarize the detailed evidence and caveats in the project sections below. “Unknown”
means the requirement still needs verification, even when a tool calls ordinary Git commands.

| Requirement | GHA | OS | GAS | OG | GW |
|---|---|---|---|---|---|
| Independent CLI, runnable via `uvx` | Mismatch: Electron app | Partial: Python CLI; `uvx` workflow unverified | Mismatch: script/service, not specified CLI | Mismatch: Obsidian plugin | Mismatch: shell watcher, not Python CLI |
| Init updates `AGENTS.md` and linked guidance | Unknown | Unknown | Unknown | Unknown | Unknown |
| Agent registration, last-session shutdown, crash recovery | Unknown | Unknown | Unknown | Unknown | Unknown |
| One coordinated process per checkout | Partial: serializes passes within its manager | Partial: PID lock, not proven atomic or checkout-scoped | Partial: in-process thread lock | Partial: queued plugin actions | Unknown |
| Include tracked and new non-ignored changes | Partial | Partial | Partial | Partial | Partial |
| Preserve existing staged work and ask before including it | Mismatch | Mismatch | Mismatch | Mismatch for automatic all-changes mode | Mismatch for directory mode |
| 10-second quiet period and 30-second maximum | Mismatch: 30-second quiet, five-minute cap | Partial: periodic timer | Partial: five-second debounce, no evidenced cap | Partial: timers and debounce in minutes | Partial: quiet timer only evidenced |
| Current branch and configured upstream; ask if absent | Mismatch: uses `origin` and can create upstream | Mismatch: configured remote and branch | Mismatch: default branch and `origin` | Partial: tracking-aware behavior | Partial: remote/branch options |
| Safe rebase of unpublished work; never force-push | Partial | Partial | Partial | Partial: merge is default, rebase configurable | Partial: pull/rebase optional |
| Offline editing, retry and actionable status | Partial | Partial | Partial; retry gap identified | Partial | Unknown |
| Agent resolves conflicts, user escalation if needed | Mismatch: keep-both plus copied prompt | Mismatch: stops on conflict | Partial: reports failed rebase | Mismatch: manual Obsidian workflow | Unknown |
| Preserve both sides, history, and concurrent edits | Partial: targeted implementation and tests; gaps remain | Unknown | Unknown; stash/rebase path needs testing | Partial: manual conflict resolution | Unknown |
| Pause around other Git operations | Partial: detects rebase, merge, detached HEAD | Unknown | Unknown | Unknown | Partial: optional merge check |
| Secret detection across pending push; approval override | Partial: optional pre-send command, not verified as this policy | Unknown | Mismatch: README relies on ignore rules | Unknown | Unknown |
| Git LFS and partial-failure semantics | Mismatch: size-based exclusion affects LFS candidates | Mismatch: push bypasses pre-push hook | Unknown | Partial: documented LFS support | Unknown |
| Human and machine-readable persistent status | Partial: desktop UI and internal status | Partial: CLI status and logs | Partial: CLI status, logs, notifications | Partial: Obsidian UI | Unknown |

“Partial” for ordinary Git mechanics does not imply the complete safety contract, especially for
concurrent writes, crashes, worktrees, unusual Git hooks, or remote failures.

## Detailed evaluation

### GitHub AutoSync

**What fits.** Its sync pass commits local changes, fetches, rebases, and pushes, with explicit
classification of offline, authentication, and identity failures. It detects a repository already
in a merge or rebase and handles linked worktree Git paths. Its conflict code keeps the upstream
file and writes the local version to a separately named file; it attempts to preserve tracked edits
made during a rebase. The repository includes tests with real Git repositories for two-clone
conflicts and a save made while a rebase fails.

Sources: [sync pass](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/sync.ts#L11-L29),
[repository state](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/detect.ts#L15-L41),
[conflict implementation](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/resolve.ts#L6-L59),
and [preservation tests](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/guarantees.test.ts#L56-L90).
These tests were inspected, not run; they cover selected cases rather than every possible failure.

**Where it differs from the requested product:**

- Its desktop interface asks the user to copy an AI prompt; the documented workflow is not an
  autonomous agent assignment and escalation protocol.
  [README](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/README.md)
- The normal sync code uses `origin` for fetching and, when there is no upstream, can publish with
  `push -u origin HEAD`; this differs from asking the user before choosing an upstream.
  [Exchange](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/sync.ts#L169-L210)
- It runs `git add -A` for the chosen scope and commits the resulting index, including previously
  staged files. That conflicts with preserving staged work and asking before including it.
  [Staging and commit](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/pass.ts#L94-L139)
- Its default auto timing is a 30-second quiet period, a five-minute cap, and a one-minute pull
  interval, rather than the requested 10-second quiet period and 30-second cap.
  [Timer constants](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/shared/status.ts#L8-L25)
- The staging code excludes files at or above 95 MiB based on filesystem size, before checking
  whether they are LFS-managed. An LFS-tracked file of that size would therefore be held back by
  this path; successful ordinary LFS support must not be inferred from Git usage.
  [Size filter](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/pass.ts#L23-L24)
  and [staging implementation](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/pass.ts#L67-L126)
- An optional before-send command exists, but it is not evidence of built-in secret scanning of
  every pending commit or per-incident approval.
  [Before-send command](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/sync.ts#L130-L139)

**Safety questions found by static inspection:** `foldOwnCommits` performs a soft reset and returns
zero when its replacement commit fails; the caller interprets zero as a clean result. This appears
capable of reporting a level state despite that failure. Separately, the conflict parking code maps
any read error to `null`, which its restore path treats as a deletion. These are source-level
observations, not reproduced incidents; neither should be adopted without targeted tests and
resolution.
[Fold path](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/pass.ts#L204-L214),
[caller](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/sync.ts#L201-L205),
and [parking and restore](https://github.com/yaseenarshad/github-autosync/blob/ad4118e1f4fd898f1abe99ab6c184955b9171fbf/desktop/src/main/git/resolve.ts#L101-L120).

**Reuse verdict:** Strongest conflict-engine reference; potentially reusable MIT code, but not a
headless drop-in or an established implementation of the requested safety contract.

### obsidian-sync

**What fits.** A Python package exposes a CLI and offers one-shot sync, foreground and background
daemon modes, status, logs, and service installation. Its default strategy commits before pulling
with rebase and then pushes. It uses a PID file and removes stale locks.
[CLI and installation](https://github.com/alex-furrier/obsidian-sync/blob/864658b39744c760f8f79ca41a7e9ececc4f89d1/README.md),
[sync cycle](https://github.com/alex-furrier/obsidian-sync/blob/864658b39744c760f8f79ca41a7e9ececc4f89d1/src/obsidian_sync/daemon.py#L84-L165),
and [PID lock](https://github.com/alex-furrier/obsidian-sync/blob/864658b39744c760f8f79ca41a7e9ececc4f89d1/src/obsidian_sync/daemon.py#L243-L257).

**Where it differs:**

- The lock is a configured path, defaulting to one global daemon lock, rather than a demonstrated
  atomic per-checkout lease shared by participating agent sessions. The read-then-write lock
  implementation needs concurrency testing.
  [Configuration](https://github.com/alex-furrier/obsidian-sync/blob/864658b39744c760f8f79ca41a7e9ececc4f89d1/src/obsidian_sync/config.py#L28-L33)
  and [lock default](https://github.com/alex-furrier/obsidian-sync/blob/864658b39744c760f8f79ca41a7e9ececc4f89d1/src/obsidian_sync/config.py#L57-L64)
- It uses a periodic interval, configured remote and branch, and `git add -A`; it does not preserve
  a separately staged user selection in the inspected sync path. A conflict stops the daemon.
  [Daemon](https://github.com/alex-furrier/obsidian-sync/blob/864658b39744c760f8f79ca41a7e9ececc4f89d1/src/obsidian_sync/daemon.py#L58-L79)
  and [Git operations](https://github.com/alex-furrier/obsidian-sync/blob/864658b39744c760f8f79ca41a7e9ececc4f89d1/src/obsidian_sync/git_ops.py#L72-L103)
- The code uses `git commit --no-verify` and `git push --no-verify`. The latter bypasses the
  `pre-push` hook; Git LFS documents that its pre-push hook uploads associated LFS objects.
  Consequently, this path cannot be assumed to provide the required LFS behavior and may also
  bypass repository-specific checks. Server-side validation or other upload mechanisms can alter
  the outcome; none was tested here.
  [Commit and push](https://github.com/alex-furrier/obsidian-sync/blob/864658b39744c760f8f79ca41a7e9ececc4f89d1/src/obsidian_sync/git_ops.py#L79-L85),
  [push](https://github.com/alex-furrier/obsidian-sync/blob/864658b39744c760f8f79ca41a7e9ececc4f89d1/src/obsidian_sync/git_ops.py#L123-L132),
  and [Git LFS pre-push documentation](https://github.com/git-lfs/git-lfs/blob/debca01ac1ca27a20cc30ac6870151b48c014881/docs/man/git-lfs-pre-push.adoc).
- It defers synchronization when it detects Obsidian running, which is an intentional product
  behavior but not the requested agent-session policy.
  [Detection](https://github.com/alex-furrier/obsidian-sync/blob/864658b39744c760f8f79ca41a7e9ececc4f89d1/src/obsidian_sync/daemon.py#L107-L110).

**Reuse verdict:** Useful Python CLI/daemon reference, but its Git safety, hooks, LFS, conflict
handling, and session lifecycle require substantial changes before use.

### git-auto-sync

**What fits.** The script watches saves, debounces commits, pulls with rebase, records status, and
installs macOS or Windows background services. It serializes its worker threads with an in-process
lock. Its README describes notifications and recovery attempts.
[README](https://github.com/AIZIU/git-auto-sync/blob/5e8c829a18e243f0f8586ee06e16923bf8859376/README.md)
and [worker](https://github.com/AIZIU/git-auto-sync/blob/5e8c829a18e243f0f8586ee06e16923bf8859376/sync.py#L339-L393).

**Where it differs:**

- It publishes only from the detected default branch, uses `origin`, and stages with `git add -A`.
  The pull path also selects the default branch. This does not meet current-branch/upstream and
  staged-work requirements.
  [Git operations](https://github.com/AIZIU/git-auto-sync/blob/5e8c829a18e243f0f8586ee06e16923bf8859376/sync.py#L178-L244)
- It defaults to a five-second debounce, 30-minute initial polling, two-minute polling after
  graduation, and nighttime pull suppression; a 30-second maximum for continuous editing was not
  established.
  [Defaults](https://github.com/AIZIU/git-auto-sync/blob/5e8c829a18e243f0f8586ee06e16923bf8859376/sync.py#L144-L155)
- The dirty-tree pull path stashes untracked files, attempts rebase, and then attempts stash pop.
  Its guarantees for concurrent edits, an interrupted rebase, and stash failure need independent
  tests.
  [Pull path](https://github.com/AIZIU/git-auto-sync/blob/5e8c829a18e243f0f8586ee06e16923bf8859376/sync.py#L199-L223)
- **Retry gap observed statically:** after a successful local commit and failed push, the retry path
  calls `commit_and_push` again, but that function returns “nothing to commit” when the working
  tree has no new changes, before attempting a push. Therefore that retry does not itself establish
  publication of the already-created commit. This was not reproduced at runtime.
  [Commit/push guard](https://github.com/AIZIU/git-auto-sync/blob/5e8c829a18e243f0f8586ee06e16923bf8859376/sync.py#L225-L244)
  and [retry](https://github.com/AIZIU/git-auto-sync/blob/5e8c829a18e243f0f8586ee06e16923bf8859376/sync.py#L351-L372)
- The README says sensitive files are handled through `.gitignore`, not a pending-history secret
  scanner with user approval.
  [Secret FAQ](https://github.com/AIZIU/git-auto-sync/blob/5e8c829a18e243f0f8586ee06e16923bf8859376/README.md#L108-L109)

**Reuse verdict:** Reference only unless branch handling, staged state, retry, and lifecycle are
redesigned and validated.

### Obsidian Git

**What fits.** It has scheduled commit, pull, and push routines; a queue for Git actions; source
control and conflict UI; and documented Git LFS support. It is the only shortlisted project whose
reviewed documentation explicitly states LFS support, although the exact failure contract requested
here remains unverified.
[Automatic routines](https://github.com/Vinzent03/obsidian-git/blob/4ede23cc4bbe3b7ee3fdc4b7a04e02583b690531/src/automaticsManager.ts#L30-L56),
[LFS documentation](https://github.com/Vinzent03/obsidian-git/blob/4ede23cc4bbe3b7ee3fdc4b7a04e02583b690531/docs/Integration%20with%20other%20tools.md#L3-L21),
and [conflict guide](https://github.com/Vinzent03/obsidian-git/blob/4ede23cc4bbe3b7ee3fdc4b7a04e02583b690531/docs/Conflict%20resolution.md#L1-L24).

**Where it differs:** It runs as an Obsidian plugin, defaults to merge rather than rebase, and its
documented conflict workflow requires human action; rebase continuation is delegated to a terminal
or Git client. Automatic routines use an all-changes commit mode, not the requested consent
protocol for pre-existing staged work. Timers use minute-based settings, so the exact requested
quiet-period and cap behavior is not established.
[Defaults](https://github.com/Vinzent03/obsidian-git/blob/4ede23cc4bbe3b7ee3fdc4b7a04e02583b690531/src/constants.ts#L14-L33),
[auto commit](https://github.com/Vinzent03/obsidian-git/blob/4ede23cc4bbe3b7ee3fdc4b7a04e02583b690531/src/automaticsManager.ts#L166-L194),
and [commit modes](https://github.com/Vinzent03/obsidian-git/blob/4ede23cc4bbe3b7ee3fdc4b7a04e02583b690531/src/gitActions.ts#L398-L405).

**Reuse verdict:** Strong reference for LFS setup and human conflict UX; unsuitable as the
independent agent-session daemon without a separate integration layer and a safety review.

### gitwatch

**What fits.** A small Bash watcher stages and commits changes after a quiet interval and can push.
Pull/rebase before pushing and an initial commit check are optional.
[Usage](https://github.com/gitwatch/gitwatch/blob/04735cfa8973a5ba425ec4befb25ecb04074465c/gitwatch.sh#L56-L83)
and [commit path](https://github.com/gitwatch/gitwatch/blob/04735cfa8973a5ba425ec4befb25ecb04074465c/gitwatch.sh#L375-L455).

**Where it differs:** Directory mode stages with `git add --all .` and commits the index without an
approval step. The core loop is driven by local filesystem events; continuous remote polling, the
requested conflict protocol, per-agent lifetime, LFS failure semantics, and secret checks were not
established. Its optional merge check is disabled by default; it does not establish protection for
every concurrent Git operation.
[Defaults](https://github.com/gitwatch/gitwatch/blob/04735cfa8973a5ba425ec4befb25ecb04074465c/gitwatch.sh#L40-L52),
[directory staging](https://github.com/gitwatch/gitwatch/blob/04735cfa8973a5ba425ec4befb25ecb04074465c/gitwatch.sh#L264-L274),
and [watch loop](https://github.com/gitwatch/gitwatch/blob/04735cfa8973a5ba425ec4befb25ecb04074465c/gitwatch.sh#L457-L482).

**Reuse verdict:** A compact reference for filesystem watching, not a complete safety or
collaboration foundation. GPL-3.0 reuse implications depend on the intended integration and require
appropriate license review.

## Requirement-focused scenarios

| Scenario | What the evidence says | Remaining decision or verification |
|---|---|---|
| Two people edit the same note | GHA keeps separate copies and has a two-clone test; OG provides a manual conflict UI. OS stops on a conflict. | Agent assignment, semantic resolution, delete/rename/binary cases, and recovery after interruption are not established. |
| A user staged a partial change before an agent starts | GHA, OS, GAS, GW directory mode, and OG automatic all-changes mode can commit existing staged content. | None of those inspected paths implements the agreed ask-before-including policy. |
| A large LFS-managed file is saved | OG documents LFS support. GHA filters files by working-tree size; OS bypasses the normal LFS pre-push hook. | Verify actual object upload, failed upload, recovery, remote visibility, and accurate partial status for any selected approach. |
| A push fails after a local commit | OS checks whether it is ahead on later cycles. GAS's immediate retry can encounter its “nothing to commit” guard. | Verify reconnect behavior, retries, and absence of false success under network and authentication failures. |
| A file changes during a rebase | GHA has targeted preservation code and a test for a late save during a failing rebase. | Run a wider matrix including read/write errors, power loss, binary files, external Git operations, and multiple agents. |
| A new branch has no upstream | GHA may create one under `origin`; OS and GAS use configured/default branch policies. | The agreed policy is to ask the user, not silently choose a destination. |
| A secret was committed locally and then removed from the working tree | No reviewed candidate was shown to enforce pending-history scanning plus per-incident approval. | Evaluate the scanner and its failure mode before publishing; ordinary working-tree checks are insufficient. |

## Due diligence before a reuse decision

The following are assessment criteria, not claims that a candidate already passes them:

1. Run isolated real-Git tests with two clones and a local bare remote; inject interruptions,
   concurrent saves, staged changes, rename/delete/binary conflicts, and push races. Verify all
   versions and the index before and after each failure.
2. Exercise real Git LFS with successful and failed object transfers, including files above 95 MiB;
   verify actual remote objects rather than merely a successful Git push.
3. Test secret detection against every commit in the pending push, scanner failure, false positives,
   and explicit one-incident approval.
4. Verify one process per checkout, multiple agent registrations, stale sessions, final shutdown,
   pre-existing Git operations, hooks, worktrees, and current-branch/upstream behavior.
5. Assess license obligations and the practical cost of extracting code from an Electron app or
   adapting a Python daemon. Do not equate an MIT license with a stable supported API.
6. Confirm command availability through `uvx`, supported agent hosts, platforms, packaging, and
   operational ownership. These details remain open in the specification.

The existing specification's safety requirements remain authoritative. Any narrower first release
or change to the conflict policy requires a separate product decision.
