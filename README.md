# agentic-planning-surface
A project dedicated to only planning for my opensource agentic projects

## Git autosync

The watcher uses Git, Git LFS, Gitleaks, and `uv`:

```bash
uv run scripts/ai-autosync-git.py start .
uv run scripts/ai-autosync-git.py sync .
uv run scripts/ai-autosync-git.py status .
```

Run `start` as a detached background process so it outlives the agent session; only one watcher
can own a checkout, and its PID is recorded in `.git/ai-autosync/watcher.json`. `sync` requests an
immediate
cycle from an existing watcher, or runs one when no watcher is active. Add `--local-only`
to `start` or `sync` to create local commits without fetching or publishing.

The watcher blocks publishing if secret scanning or LFS upload fails. It stops for agent
intervention when incoming commits require integration; it does not automatically rebase a
checkout that other processes may be editing. See the
[autosync guidelines](.agents/guidelines/autosync.guidelines.md) for approvals and recovery.
Before publishing, Gitleaks scans pending Git history and the local LFS object cache. Scanning the
whole cache can flag older objects; secret detection cannot guarantee that every secret is found.

The root `.gitattributes` is imported from the shared boilerplate and tracks many binary formats
with Git LFS. It normalizes text files, including `.bat` and `.cmd`, to LF on checkout.
When repository attributes change, autosync runs `git add --renormalize` on the tracked working
tree, converting existing files into or out of LFS according to the new attributes. Git LFS must
be installed and its filters configured for LFS-tracked files. This creates a new commit; it does
not rewrite old commits or remove historical Git blobs or LFS objects.
