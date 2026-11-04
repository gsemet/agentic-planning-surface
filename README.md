# agentic-planning-surface
A project dedicated to only planning for my opensource agentic projects

## Git autosync

The session-bound watcher uses Git, Git LFS, Gitleaks, and `uv`:

```bash
uv run scripts/ai-autosync-git.py start .
uv run scripts/ai-autosync-git.py sync .
uv run scripts/ai-autosync-git.py status .
```

Run `start` in the agent host's background-process facility. `sync` requests an immediate
cycle from an existing watcher, or runs one when no watcher is active. Add `--local-only`
to `start` or `sync` to create local commits without fetching or publishing.

The watcher blocks publishing if secret scanning or LFS upload fails. It stops for agent
intervention when incoming commits require integration; it does not automatically rebase a
checkout that other processes may be editing. See the
[autosync guidelines](.agents/guidelines/autosync.guidelines.md) for approvals and recovery.
Before publishing, Gitleaks scans pending Git history and the local LFS object cache. Scanning the
whole cache can flag older objects; secret detection cannot guarantee that every secret is found.
