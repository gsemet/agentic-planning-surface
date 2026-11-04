# Git autosync guidelines

Run commands from the repository root. Before starting a watcher, check whether one is already
running for this checkout:

```bash
uv run scripts/ai-autosync-git.py status .
cat .git/ai-autosync/watcher.json
```

If `watcher.json` names a live process, reuse it; do not start another one. Otherwise start the
watcher as a detached background process so it outlives the agent's turn and session:

```bash
uv run scripts/ai-autosync-git.py start .
```

A process attached to the agent's shell stops when that shell or session ends, so it does not
provide continuous synchronization. Only one watcher can own a checkout: a second `start` exits
with "Another autosync process owns this checkout." Stop the watcher with `kill PID`, using the PID
recorded in `.git/ai-autosync/watcher.json`; it runs a final cycle before exiting.

When the watcher exits with an action-required message, inspect its status, resolve Git conflicts
and other reported problems without discarding changes, then restart it. Remote integration that
requires rewriting the checkout is intentionally handed to the agent rather than attempted while
other processes may be editing. Never force-push.

Run an immediate one-shot synchronization when needed:

```bash
uv run scripts/ai-autosync-git.py sync .
```

If a watcher is running, this requests a new cycle from it rather than starting a competing Git
operation. Use `--local-only` on `start` or `sync` to save local commits without fetching, scanning,
or publishing; the watcher retains its selected mode, and a local-only request is refused by a
watcher that can publish.

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
used; otherwise the watcher stops instead of committing raw content. Do not set `core.autocrlf`
to override the attributes.

Git, Git LFS, and Gitleaks must be available. The tool preserves Git hooks and does not push when
secret scanning or the LFS upload fails. Its status and approvals are local to the checkout.
