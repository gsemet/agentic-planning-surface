# Git autosync guidelines

Run commands from the repository root. Start the session-bound watcher using the host's
background-process facility:

```bash
uv run scripts/ai-autosync-git.py start .
```

Keep the process attached to the agent session. Do not start another watcher for the same
checkout. When it exits with an action-required message, inspect its status:

```bash
uv run scripts/ai-autosync-git.py status .
```

Resolve Git conflicts and other reported problems without discarding changes, then restart the
watcher. A remote integration that requires rewriting the checkout is intentionally handed to
the agent rather than attempted while other processes may be editing. Never force-push.

Run an immediate one-shot synchronization when needed:

```bash
uv run scripts/ai-autosync-git.py sync .
```

If the watcher is already running, this requests a new cycle from that watcher rather than
starting a competing Git operation. Use `--local-only` on `start` or `sync` to save local
commits without fetching or publishing; the watcher retains its selected mode.

Existing staged changes and detected secrets require explicit human approval. Show the user the
reported incident; never approve it on the user's behalf. An approval applies only to the exact
index or pending push identified in the incident:

```bash
uv run scripts/ai-autosync-git.py approve . INCIDENT_ID
```

Git, Git LFS, and Gitleaks must be available. The tool preserves Git hooks and does not push when
secret scanning or the LFS upload fails. Its status and approvals are local to the checkout.
