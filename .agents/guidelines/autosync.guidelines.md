# Git autosync guidelines

Run commands from the repository root. Every agent session that works in this checkout joins one
autosync group. Group members coordinate through `.git/ai-autosync/`: a kernel file lock elects a
single leader that watches and synchronizes; the others are followers that take over within about
a second when the leader exits. Members leave the group when their owner process ends.

## Joining the group

First read the agent host PID in a normal, non-detached command, because a detached command has a
supervisor as its parent:

```bash
echo $PPID
```

Then check the group and join it with a detached background process, so membership outlives the
agent's turn:

```bash
uv run scripts/ai-autosync-git.py status .
uv run scripts/ai-autosync-git.py join . --owner-pid HOST_PID
```

`join` does not change whether autosync is enabled; it only adds this session as a candidate
leader. Join once per session; if `status` already lists a participant with this session's owner
PID that this session started, do not join again.

## User orders apply to every session

Orders are written to a shared control file and every participant follows them:

- "start autosync": run `uv run scripts/ai-autosync-git.py start . --enable-only`, which enables
  autosync for the whole group, and join the group as above if this session is not a member yet.
  Instead of both steps, a detached `start . --owner-pid HOST_PID` enables and joins in one
  command.
- "stop autosync": run `uv run scripts/ai-autosync-git.py stop .`. The leader runs a final cycle,
  then every participant becomes idle while staying in the group, ready for the next `start`.

Add `--local-only` to `start` to save local commits without fetching, scanning, or publishing; the
mode also applies to the whole group. To leave the group entirely, stop a participant process with
`kill PID`, using a PID listed by `status`. Never kill the leader to stop synchronization; use
`stop`.

`status` prints the control state, the leader PID, and every participant with its role
(`leader`, `follower`, or `idle`).

## Action required

When synchronization needs attention, the leader disables autosync for the whole group with a
`blocked:` reason, so followers do not repeat the failure. Inspect `status`, resolve Git conflicts
and other reported problems without discarding changes, obtain any required approval, then run
`start . --enable-only`. Remote integration that requires rewriting the checkout is intentionally
handed to the agent rather than attempted while other processes may be editing. Never force-push.

Run an immediate one-shot synchronization when needed:

```bash
uv run scripts/ai-autosync-git.py sync .
```

If a leader is running, this requests a new cycle from it rather than starting a competing Git
operation; a local-only request is refused by a leader that can publish.

Existing staged changes and detected secrets require explicit human approval. Show the user the
reported incident; never approve it on the user's behalf. An approval applies only to the exact
index or pending push identified in the incident:

```bash
uv run scripts/ai-autosync-git.py approve . INCIDENT_ID
```

## Git LFS and line endings

The repository's `.gitattributes` decides which files are stored in Git LFS and how line endings
are normalized. When any `.gitattributes` file changes, the next cycle runs
`git add --renormalize .`, so existing files move into or out of Git LFS and their line endings are
normalized in a new commit. Working-tree bytes are left unchanged, and older commits are not
rewritten. Commit an attribute change through autosync rather than staging it by hand; staged
changes require approval first.

Git LFS must be installed and its filters configured (`git lfs install`) before LFS attributes are
used; otherwise synchronization stops instead of committing raw content. Do not set
`core.autocrlf` to override the attributes.

Git, Git LFS, and Gitleaks must be available. The tool preserves Git hooks and does not push when
secret scanning or the LFS upload fails. Its status, control, and approvals are local to the
checkout.
