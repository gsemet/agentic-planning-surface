#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "filelock>=3.16,<4",
#   "watchdog>=4,<7",
# ]
# ///
"""Synchronize one Git checkout while an agent session is active."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

__version__ = "1.0.0"
COMMIT_SUBJECT = "chore: autosync repository changes"
COMMIT_TRAILER = f"Authored-By: Ai-Autosync-git {__version__}"

DEFAULT_CONFIG = """\
# Timing values are in seconds.
quiet_seconds = 10
maximum_seconds = 30
poll_seconds = 30
"""

AGENT_SECTION = """\
## Git autosync

Follow the [autosync guidelines](.agents/guidelines/autosync.guidelines.md) when working in
this repository.
"""

GUIDELINES = """\
# Git autosync guidelines

Run commands from the repository root. Every agent session that works in this checkout joins one
autosync group. Group members coordinate through `.git/ai-autosync/`: a kernel file lock elects a
single leader that watches and synchronizes; the others are followers that take over within about
a second when the leader exits.

Each participant pings its coding-agent harness about once per second and exits as soon as its
session is no longer active. The harness is detected from the environment (`--harness auto`):
GitHub Copilot sessions are followed through their session-state `inuse` lock, so closing or
archiving the chat ends the participant; Claude Code and other harnesses currently fall back to the
owner process. Pass `--harness` and `--session-id` explicitly when detection is not possible.

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
"""


class SyncError(Exception):
    """An error that requires an agent or user to intervene."""


class RetryableError(Exception):
    """A network failure that can be retried."""


class ApprovalRequired(SyncError):
    """A specific operation needs human approval."""


class DeferredError(RetryableError):
    """A local operation is temporarily preventing synchronization."""


def command(
    args: list[str], cwd: Path, *, env: dict[str, str] | None = None, timeout: int = 120
) -> subprocess.CompletedProcess[str]:
    process_env = os.environ.copy()
    process_env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_EDITOR": "true"})
    if env:
        process_env.update(env)
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            env=process_env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SyncError(f"Required executable is unavailable: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RetryableError(f"{args[0]} timed out after {timeout} seconds") from exc


def git(
    root: Path, *args: str, env: dict[str, str] | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = command(["git", *args], root, env=env)
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SyncError(f"git {' '.join(args)} failed: {detail}")
    return result


def repository(path: Path) -> tuple[Path, Path]:
    path = path.resolve()
    if not path.is_dir():
        raise SyncError(f"Repository directory does not exist: {path}")
    root_result = git(path, "rev-parse", "--show-toplevel")
    root = Path(root_result.stdout.strip()).resolve()
    git_dir = git(root, "rev-parse", "--absolute-git-dir").stdout.strip()
    return root, Path(git_dir) / "ai-autosync"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2)
        stream.write("\n")
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise SyncError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SyncError(f"Expected an object in {path}")
    return data


def status(state_dir: Path, state: str, message: str, **details: Any) -> None:
    record = {"state": state, "message": message, "updated_at": time.time(), **details}
    write_json(state_dir / "status.json", record)
    print(f"[{state}] {message}", flush=True)


def incident(kind: str, *parts: str) -> str:
    payload = "\0".join((kind, *parts)).encode()
    return f"{kind}-{hashlib.sha256(payload).hexdigest()[:20]}"


def require_approval(state_dir: Path, identifier: str, message: str) -> None:
    approvals = read_json(state_dir / "approvals.json")
    if approvals.get(identifier) is True:
        return
    status(state_dir, "approval_required", message, incident=identifier)
    raise ApprovalRequired(f"{message} Human approval required for incident {identifier}")


def approve(state_dir: Path, identifier: str) -> None:
    current = read_json(state_dir / "status.json")
    if current.get("state") != "approval_required" or current.get("incident") != identifier:
        raise SyncError("The incident is not the currently pending approval")
    approvals = read_json(state_dir / "approvals.json")
    approvals[identifier] = True
    write_json(state_dir / "approvals.json", approvals)
    print(f"Approved incident {identifier}; retry synchronization.")


def consume_approval(state_dir: Path, identifier: str) -> None:
    approvals = read_json(state_dir / "approvals.json")
    if identifier in approvals:
        del approvals[identifier]
        write_json(state_dir / "approvals.json", approvals)


def config(root: Path) -> tuple[float, float, float]:
    path = root / ".agents" / "autosync.toml"
    if not path.exists():
        return 10.0, 30.0, 30.0
    try:
        with path.open("rb") as stream:
            data = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SyncError(f"Cannot read {path}: {exc}") from exc
    values = []
    for key, default in (
        ("quiet_seconds", 10),
        ("maximum_seconds", 30),
        ("poll_seconds", 30),
    ):
        value = data.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise SyncError(f"{key} must be a positive number")
        values.append(float(value))
    return values[0], values[1], values[2]


def initialize(root: Path) -> None:
    target_script = root / "scripts" / "ai-autosync-git.py"
    source_script = Path(__file__).resolve()
    if not target_script.exists():
        target_script.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_script, target_script)
    elif target_script.resolve() != source_script and target_script.read_bytes() != source_script.read_bytes():
        raise SyncError(f"Existing script differs and was not replaced: {target_script}")
    agents = root / "AGENTS.md"
    if agents.exists():
        existing = agents.read_text(encoding="utf-8")
        if ".agents/guidelines/autosync.guidelines.md" not in existing:
            with agents.open("a", encoding="utf-8") as stream:
                stream.write("\n\n" + AGENT_SECTION)
    else:
        agents.write_text("# Agent instructions\n\n" + AGENT_SECTION, encoding="utf-8")
    guidance = root / ".agents" / "guidelines" / "autosync.guidelines.md"
    guidance.parent.mkdir(parents=True, exist_ok=True)
    if not guidance.exists():
        guidance.write_text(GUIDELINES, encoding="utf-8")
    elif guidance.read_text(encoding="utf-8") != GUIDELINES:
        print(f"Existing guidance preserved: {guidance}", file=sys.stderr)
    settings = root / ".agents" / "autosync.toml"
    if not settings.exists():
        settings.write_text(DEFAULT_CONFIG, encoding="utf-8")
    print("Repository initialized. Start the watcher from an active agent session.")


def busy_operation(root: Path) -> str | None:
    for name in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"):
        result = git(root, "rev-parse", "--git-path", name).stdout.strip()
        path = Path(result)
        if not path.is_absolute():
            path = root / path
        if path.exists():
            return name
    return None


def attr_fingerprint(root: Path) -> str:
    result = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    names = sorted(
        name for name in result.stdout.split("\0")
        if name and Path(name).name == ".gitattributes"
    )
    digest = hashlib.sha256()
    for name in names:
        path = root / name
        digest.update(os.fsencode(name) + b"\0")
        try:
            digest.update(path.read_bytes())
        except FileNotFoundError:
            digest.update(b"<deleted>")
        except OSError as exc:
            raise SyncError(f"Cannot read attributes file {path}: {exc}") from exc
        digest.update(b"\0")
    return digest.hexdigest()


def check_lfs_filters(root: Path) -> None:
    result = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    names = {name for name in result.stdout.split("\0") if name and Path(name).name == ".gitattributes"}
    git_dir = Path(git(root, "rev-parse", "--absolute-git-dir").stdout.strip())
    paths = [root / name for name in names] + [git_dir / "info" / "attributes"]
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            continue
        except (OSError, UnicodeError) as exc:
            raise SyncError(f"Cannot read attributes file {path}: {exc}") from exc
        if any("filter=lfs" in line.split()[1:] for line in lines if line.strip() and not line.lstrip().startswith("#")):
            version = command(["git", "lfs", "version"], root)
            clean = git(root, "config", "--get", "filter.lfs.clean", check=False)
            smudge = git(root, "config", "--get", "filter.lfs.smudge", check=False)
            if version.returncode or not clean.stdout.strip() or not smudge.stdout.strip():
                raise SyncError(
                    "Git LFS attributes are present but its clean/smudge filters are not configured; "
                    "configure Git LFS before committing"
                )
            return


def create_commit(root: Path, state_dir: Path) -> bool:
    """Commit through a private index while holding Git's real index lock."""
    git_dir = Path(git(root, "rev-parse", "--absolute-git-dir").stdout.strip())
    index = git_dir / "index"
    lock = git_dir / "index.lock"
    try:
        lock_fd = os.open(
            lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0), 0o666
        )
    except FileExistsError as exc:
        raise SyncError("Another Git process holds the index lock") from exc
    temporary: Path | None = None
    committed = False
    owns_lock = True
    processed_attributes: str | None = None
    staged_incident: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=git_dir, prefix="autosync-index-", delete=False) as stream:
            temporary = Path(stream.name)
        env = {"GIT_INDEX_FILE": str(temporary)}
        if index.exists():
            shutil.copyfile(index, temporary)
        else:
            temporary.unlink()
            head = git(root, "rev-parse", "--verify", "HEAD", check=False)
            git(root, "read-tree", "HEAD" if head.returncode == 0 else "--empty", env=env)

        staged = git(root, "diff", "--cached", "--quiet", env=env, check=False)
        if staged.returncode not in (0, 1):
            raise SyncError(f"Cannot inspect staged changes: {staged.stderr.strip()}")
        if staged.returncode == 1:
            tree = git(root, "write-tree", env=env).stdout.strip()
            identifier = incident("staged", tree)
            require_approval(
                state_dir, identifier,
                "Existing staged changes will be committed separately; inspect them with git diff --cached.",
            )
            staged_incident = identifier
        else:
            check_lfs_filters(root)
            git(root, "add", "-A", "--", ".", env=env)
            fingerprint = attr_fingerprint(root)
            previous = read_json(state_dir / "attributes.json").get("fingerprint")
            if fingerprint != previous:
                git(root, "add", "--renormalize", "--", ".", env=env)
            processed_attributes = fingerprint

        diff = git(root, "diff", "--cached", "--quiet", env=env, check=False)
        if diff.returncode == 0:
            if processed_attributes is not None:
                write_json(state_dir / "attributes.json", {"fingerprint": processed_attributes})
            return False
        if diff.returncode != 1:
            raise SyncError(f"Cannot inspect prepared changes: {diff.stderr.strip()}")
        commit_args = ["commit", "-m", COMMIT_SUBJECT, "-m", COMMIT_TRAILER]
        result = git(root, *commit_args, env=env, check=False)
        if result.returncode:
            raise SyncError(f"Automatic commit failed: {result.stderr.strip() or result.stdout.strip()}")
        committed = True
        with os.fdopen(lock_fd, "wb") as stream:
            lock_fd = -1
            with temporary.open("rb") as prepared:
                shutil.copyfileobj(prepared, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(lock, index)
        owns_lock = False
        if processed_attributes is not None:
            write_json(state_dir / "attributes.json", {"fingerprint": processed_attributes})
        if staged_incident is not None:
            consume_approval(state_dir, staged_incident)
        return True
    except OSError as exc:
        if committed:
            raise SyncError(
                f"Commit succeeded but the index could not be updated; inspect git status: {exc}"
            ) from exc
        raise SyncError(f"Cannot prepare the Git index: {exc}") from exc
    finally:
        if lock_fd >= 0:
            os.close(lock_fd)
        if owns_lock:
            lock.unlink(missing_ok=True)
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def upstream(root: Path) -> tuple[str, str, str]:
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if branch.returncode:
        raise SyncError("Detached HEAD; select a branch before synchronizing")
    name = branch.stdout.strip()
    remote = git(root, "config", "--get", f"branch.{name}.remote", check=False)
    merge = git(root, "config", "--get", f"branch.{name}.merge", check=False)
    if remote.returncode or merge.returncode or remote.stdout.strip() == ".":
        raise SyncError(f"Branch {name} has no configured remote upstream; configure one explicitly")
    destination = merge.stdout.strip()
    if not destination.startswith("refs/heads/"):
        raise SyncError(f"Unsupported upstream reference: {destination}")
    return name, remote.stdout.strip(), destination


def scan_pending(root: Path, state_dir: Path, base: str, head: str) -> str | None:
    common = [
        "--no-banner", "--redact=100", "--exit-code=23", "--report-format=json", "--report-path=-",
    ]
    scans = [
        ["gitleaks", "git", *common, f"--log-opts={base}..{head}", str(root)],
    ]
    lfs_env = command(["git", "lfs", "env"], root)
    if lfs_env.returncode:
        raise SyncError(f"Cannot locate Git LFS objects; push blocked: {lfs_env.stderr.strip()}")
    media = next(
        (line.partition("=")[2] for line in lfs_env.stdout.splitlines()
         if line.startswith("LocalMediaDir=")),
        "",
    )
    if not media:
        raise SyncError("Git LFS did not report its local object directory; push blocked")
    if Path(media).is_dir():
        scans.append(["gitleaks", "dir", *common, media])
    files: set[str] = set()
    found = False
    for args in scans:
        result = command(args, root)
        if result.returncode == 0:
            continue
        if result.returncode != 23:
            raise SyncError(f"Gitleaks scan failed; push blocked: {result.stderr.strip()}")
        try:
            findings = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise SyncError("Gitleaks returned findings in an unreadable format; push blocked") from exc
        if not isinstance(findings, list):
            raise SyncError("Gitleaks returned an invalid findings report; push blocked")
        found = True
        files.update(str(item.get("File", "?")) for item in findings if isinstance(item, dict))
    if not found:
        return None
    identifier = incident("secrets", base, head)
    require_approval(
        state_dir, identifier,
        f"Gitleaks detected possible secrets in {', '.join(sorted(files)) or 'the pending history'}.",
    )
    return identifier


def synchronize(root: Path, state_dir: Path, *, local_only: bool = False) -> None:
    operation = busy_operation(root)
    if operation:
        raise DeferredError(f"Git operation {operation} is in progress; autosync is paused")
    if local_only:
        committed = create_commit(root, state_dir)
        status(
            state_dir, "local_only", "Local changes saved; remote synchronization is disabled.",
            committed=committed,
        )
        return
    branch, remote, destination = upstream(root)
    committed = create_commit(root, state_dir)
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    fetched = git(root, "fetch", "--", remote, check=False)
    if fetched.returncode:
        raise RetryableError(f"Fetch failed; local changes remain committed: {fetched.stderr.strip()}")
    upstream_hash = git(root, "rev-parse", "--verify", "@{upstream}").stdout.strip()
    counts = git(root, "rev-list", "--left-right", "--count", f"{upstream_hash}...{head}")
    behind, ahead = (int(value) for value in counts.stdout.split())
    if behind:
        raise SyncError(
            f"Upstream has {behind} new commit(s); agent integration is required. "
            "Autosync will not rewrite a checkout while another process may be editing it."
        )
    if ahead:
        lfs_version = command(["git", "lfs", "version"], root)
        if lfs_version.returncode:
            raise SyncError("Git LFS is unavailable; push blocked")
        secret_incident = scan_pending(root, state_dir, upstream_hash, head)
        lfs = command(["git", "lfs", "push", remote, head], root)
        if lfs.returncode:
            raise RetryableError(f"Git LFS upload failed; Git push withheld: {lfs.stderr.strip()}")
        pushed = git(root, "push", "--", remote, f"{head}:{destination}", check=False)
        if pushed.returncode:
            raise RetryableError(f"Push failed; local commits are preserved: {pushed.stderr.strip()}")
        if secret_incident is not None:
            consume_approval(state_dir, secret_incident)
    current_head = git(root, "rev-parse", "HEAD").stdout.strip()
    pending = git(root, "status", "--porcelain", "--untracked-files=normal").stdout.strip()
    if current_head != head or pending:
        status(
            state_dir, "pending", "New local changes remain for the next synchronization.",
            branch=branch, head=head, committed=committed,
        )
    else:
        status(
            state_dir, "synced", f"Branch {branch} is synchronized.",
            branch=branch, head=head, committed=committed,
        )


class Changes(FileSystemEventHandler):
    def __init__(self, root: Path) -> None:
        self.root = root
        self.event = threading.Event()
        self._lock = threading.Lock()
        self.first: float | None = None
        self.last: float | None = None

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type not in {"created", "modified", "deleted", "moved"}:
            return
        paths = [event.src_path]
        if hasattr(event, "dest_path"):
            paths.append(event.dest_path)
        relevant = False
        for value in paths:
            if not value:
                continue
            path = Path(os.fsdecode(value))
            try:
                relative = path.relative_to(self.root)
            except ValueError:
                continue
            if relative.parts and relative.parts[0] != ".git":
                relevant = True
        if relevant:
            now = time.monotonic()
            with self._lock:
                if self.first is None:
                    self.first = now
                self.last = now
            self.event.set()

    def due(self, quiet: float, maximum: float) -> bool:
        with self._lock:
            now = time.monotonic()
            return self.first is not None and self.last is not None and (
                now - self.last >= quiet or now - self.first >= maximum
            )

    def clear(self) -> None:
        with self._lock:
            self.first = self.last = None
            self.event.clear()


def run_once(root: Path, state_dir: Path, *, local_only: bool = False) -> int:
    try:
        synchronize(root, state_dir, local_only=local_only)
        return 0
    except DeferredError as exc:
        status(state_dir, "waiting", str(exc))
        return 2
    except RetryableError as exc:
        status(state_dir, "offline", str(exc))
        return 2
    except ApprovalRequired as exc:
        print(str(exc), file=sys.stderr, flush=True)
        return 1
    except SyncError as exc:
        status(state_dir, "action_required", str(exc))
        print(str(exc), file=sys.stderr, flush=True)
        return 1


FOLLOWER_POLL_SECONDS = float(os.environ.get("AI_AUTOSYNC_FOLLOWER_POLL", "1.0"))


def pid_alive(pid: int) -> bool:
    """Check a process without signalling it (os.kill would terminate it on Windows)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


class Harness:
    """Session liveness for one coding-agent harness.

    Participants ping ``alive()`` about once per second and leave the group as soon as it returns
    False. The generic harness only follows the owner process; subclasses add the harness's own
    notion of an active session. To support a new harness, subclass, implement ``detect``,
    ``session_from_env``, and ``alive``, then register it in ``HARNESSES``.
    """

    name = "generic"

    def __init__(self, owner_pid: int | None = None, session_id: str | None = None) -> None:
        self.owner_pid = owner_pid
        self.session_id = session_id

    @classmethod
    def detect(cls, env: dict[str, str]) -> bool:
        """Return True when the current process runs inside this harness."""
        return False

    @classmethod
    def session_from_env(cls, env: dict[str, str]) -> str | None:
        return None

    def alive(self) -> bool:
        return self.owner_pid is None or pid_alive(self.owner_pid)

    def describe(self) -> dict[str, Any]:
        return {"harness": self.name, "owner_pid": self.owner_pid, "session_id": self.session_id}


class CopilotHarness(Harness):
    """GitHub Copilot (CLI, VS Code agent host).

    The runtime keeps ``$COPILOT_HOME/session-state/<id>/inuse.<runtime-pid>.lock`` while the
    session is open and removes it when the session is closed or archived, even if the runtime
    process keeps serving other sessions.
    """

    name = "copilot"

    def __init__(self, owner_pid: int | None = None, session_id: str | None = None) -> None:
        super().__init__(owner_pid, session_id)
        home = Path(os.environ.get("COPILOT_HOME") or Path.home() / ".copilot")
        self.session_dir = home / "session-state" / session_id if session_id else None

    @classmethod
    def detect(cls, env: dict[str, str]) -> bool:
        return bool(env.get("COPILOT_AGENT_SESSION_ID"))

    @classmethod
    def session_from_env(cls, env: dict[str, str]) -> str | None:
        return env.get("COPILOT_AGENT_SESSION_ID") or None

    def alive(self) -> bool:
        if not super().alive():
            return False
        if self.session_dir is None:
            return True
        for lock in self.session_dir.glob("inuse.*.lock"):
            pid = lock.name.split(".")[1]
            if pid.isdigit() and pid_alive(int(pid)):
                return True
        return False


class ClaudeCodeHarness(Harness):
    """Claude Code. Only owner-process liveness is implemented.

    Claude Code sets ``CLAUDECODE=1`` for the commands it runs and exposes ``SessionStart`` and
    ``SessionEnd`` hooks (with ``session_id`` on stdin). A fuller integration can join from
    ``SessionStart`` and mark the session ended from ``SessionEnd``.
    """

    name = "claude-code"

    @classmethod
    def detect(cls, env: dict[str, str]) -> bool:
        return env.get("CLAUDECODE") == "1"


class OmpHarness(Harness):
    """oh-my-pi (omp). Not detected automatically; only owner-process liveness is implemented.

    omp loads TypeScript extensions from ``.omp/extensions`` whose ``session_start`` and
    ``session_shutdown`` events, with ``ctx.cwd`` and ``ctx.sessionManager``, can join the group
    and end the session.
    """

    name = "omp"


HARNESSES: dict[str, type[Harness]] = {
    harness.name: harness for harness in (CopilotHarness, ClaudeCodeHarness, OmpHarness, Harness)
}


def resolve_harness(
    name: str, owner_pid: int | None, session_id: str | None, env: dict[str, str] | None = None
) -> Harness:
    env = dict(os.environ if env is None else env)
    if name == "auto":
        kind = next((h for h in HARNESSES.values() if h.detect(env)), Harness)
    else:
        kind = HARNESSES[name]
    return kind(owner_pid, session_id or kind.session_from_env(env))


def read_control(state_dir: Path) -> dict[str, Any]:
    try:
        data = read_json(state_dir / "control.json")
    except SyncError:
        data = {}
    return {
        **data,
        "enabled": data.get("enabled", True) is not False,
        "local_only": data.get("local_only") is True,
    }


def set_control(
    state_dir: Path, *, enabled: bool, reason: str, local_only: bool | None = None
) -> dict[str, Any]:
    current = read_control(state_dir)
    record = {
        "enabled": enabled,
        "local_only": current["local_only"] if local_only is None else local_only,
        "reason": reason,
        "updated_at": time.time(),
        "updated_by_pid": os.getpid(),
    }
    write_json(state_dir / "control.json", record)
    return record


def participants(state_dir: Path) -> list[dict[str, Any]]:
    """Return live participants and remove records left by crashed processes."""
    found = []
    for path in sorted((state_dir / "participants").glob("*.json")):
        try:
            data = read_json(path)
        except SyncError:
            continue
        pid = data.get("pid")
        if not isinstance(pid, int) or not pid_alive(pid):
            path.unlink(missing_ok=True)
            continue
        found.append(data)
    return found


def lead(
    root: Path, state_dir: Path, stop: threading.Event, keep_running: Any
) -> int:
    """Synchronize while this process holds the checkout lock and autosync stays enabled."""
    quiet, maximum, poll = config(root)
    changes = Changes(root)
    observer = Observer()
    observer.schedule(changes, str(root), recursive=True)
    watcher_path = state_dir / "watcher.json"
    observer.start()
    next_poll = 0.0
    backoff = 5.0
    local_only = read_control(state_dir)["local_only"]
    try:
        write_json(watcher_path, {"pid": os.getpid(), "local_only": local_only})
        while keep_running():
            control = read_control(state_dir)
            if not control["enabled"]:
                break
            if control["local_only"] != local_only:
                local_only = control["local_only"]
                write_json(watcher_path, {"pid": os.getpid(), "local_only": local_only})
                next_poll = 0.0
            now = time.monotonic()
            requested = state_dir / "sync-request.json"
            if now >= next_poll or changes.due(quiet, maximum) or requested.exists():
                requested.unlink(missing_ok=True)
                changes.clear()
                result = run_once(root, state_dir, local_only=local_only)
                if result == 1:
                    return 1
                if result == 2:
                    next_poll = time.monotonic() + backoff
                    backoff = min(backoff * 2, 120.0)
                else:
                    next_poll = time.monotonic() + poll
                    backoff = 5.0
            changes.event.wait(timeout=1.0)
            changes.event.clear()
        # Final cycle before handing over, stopping, or losing the owning session.
        return run_once(root, state_dir, local_only=read_control(state_dir)["local_only"])
    finally:
        observer.stop()
        observer.join()
        watcher_path.unlink(missing_ok=True)


def participate(root: Path, state_dir: Path, harness: Harness) -> int:
    """Join the participant group: lead while holding the lock, otherwise stand by."""
    stop = threading.Event()

    def request_stop(_signum: int, _frame: Any) -> None:
        stop.set()

    for name in ("SIGTERM", "SIGINT", "SIGHUP"):
        number = getattr(signal, name, None)
        if number is not None:
            signal.signal(number, request_stop)

    def keep_running() -> bool:
        return not stop.is_set() and harness.alive()

    record = state_dir / "participants" / f"{os.getpid()}.json"
    lock = FileLock(str(state_dir / "sync.lock"))
    role: str | None = None

    def announce(new_role: str) -> None:
        nonlocal role
        write_json(record, {
            "pid": os.getpid(), **harness.describe(), "role": new_role, "since": time.time(),
        })
        if new_role != role:
            print(f"[participant] pid {os.getpid()} is now {new_role}.", flush=True)
        role = new_role

    try:
        while keep_running():
            if not read_control(state_dir)["enabled"]:
                if role != "idle":
                    announce("idle")
                stop.wait(FOLLOWER_POLL_SECONDS)
                continue
            try:
                lock.acquire(timeout=0)
            except Timeout:
                if role != "follower":
                    announce("follower")
                stop.wait(FOLLOWER_POLL_SECONDS)
                continue
            try:
                announce("leader")
                result = lead(root, state_dir, stop, keep_running)
            finally:
                lock.release()
            if result == 1:
                current = read_json(state_dir / "status.json")
                set_control(
                    state_dir, enabled=False,
                    reason=f"blocked: {current.get('message', 'intervention required')}",
                )
            announce("idle" if not read_control(state_dir)["enabled"] else "follower")
        return 0
    finally:
        record.unlink(missing_ok=True)
        if not stop.is_set() and not harness.alive():
            print(f"[participant] {harness.name} session ended; leaving.", flush=True)


def request_sync(state_dir: Path, *, local_only_requested: bool = False) -> None:
    watcher = read_json(state_dir / "watcher.json")
    pid = watcher.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        raise SyncError("Another Git sync is in progress; no running leader accepted the request")
    if local_only_requested and watcher.get("local_only") is not True:
        raise SyncError("The running leader can publish; refusing a local-only sync request")
    if not pid_alive(pid):
        raise SyncError("The recorded leader is no longer running")
    write_json(state_dir / "sync-request.json", {"requested_at": time.time()})
    mode = "local-only" if watcher.get("local_only") is True else "remote"
    print(f"Synchronization requested from the running leader ({mode} mode).")


def describe(state_dir: Path) -> dict[str, Any]:
    leader = read_json(state_dir / "watcher.json")
    leader_pid = leader.get("pid") if isinstance(leader.get("pid"), int) else None
    return {
        "status": read_json(state_dir / "status.json"),
        "control": read_control(state_dir),
        "leader_pid": leader_pid if leader_pid and pid_alive(leader_pid) else None,
        "participants": participants(state_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("init", "start", "join", "stop", "sync", "status"):
        subparser = subparsers.add_parser(action)
        subparser.add_argument("path", nargs="?", type=Path, default=Path("."))
        if action in ("start", "sync"):
            subparser.add_argument(
                "--local-only", action="store_true",
                help="commit locally without fetching, scanning, or publishing",
            )
        if action in ("start", "join"):
            subparser.add_argument(
                "--owner-pid", type=int, default=None,
                help="leave the group when this process (the agent host) exits",
            )
            subparser.add_argument(
                "--harness", choices=["auto", *HARNESSES], default="auto",
                help="coding-agent harness whose session liveness is pinged (default: detect)",
            )
            subparser.add_argument(
                "--session-id", default=None,
                help="harness session to follow (default: read from the harness environment)",
            )
        if action == "start":
            subparser.add_argument(
                "--enable-only", action="store_true",
                help="enable autosync for all participants without joining",
            )
    approval = subparsers.add_parser("approve")
    approval.add_argument("path", type=Path)
    approval.add_argument("incident")
    args = parser.parse_args()
    try:
        root, state_dir = repository(args.path)
        state_dir.mkdir(parents=True, exist_ok=True)
        if args.action == "init":
            initialize(root)
            return 0
        if args.action == "status":
            print(json.dumps(describe(state_dir), indent=2))
            return 0
        if args.action == "approve":
            approve(state_dir, args.incident)
            return 0
        if args.action == "stop":
            set_control(state_dir, enabled=False, reason="stopped by user")
            count = len(participants(state_dir))
            print(f"Autosync stopped for all sessions; {count} participant(s) now idle.")
            return 0
        if args.action in ("start", "join"):
            harness = resolve_harness(args.harness, args.owner_pid, args.session_id)
            if not harness.alive():
                raise SyncError(f"No active {harness.name} session: {harness.describe()}")
        if args.action == "join":
            control = read_control(state_dir)
            state = "enabled" if control["enabled"] else f"stopped ({control.get('reason', 'stopped')})"
            print(f"Joining the autosync group; autosync is currently {state}.", flush=True)
            return participate(root, state_dir, harness)
        if args.action == "start":
            set_control(state_dir, enabled=True, local_only=args.local_only, reason="started by user")
            mode = "local-only" if args.local_only else "remote"
            print(f"Autosync enabled for all sessions ({mode} mode).", flush=True)
            if args.enable_only:
                return 0
            return participate(root, state_dir, harness)
        with FileLock(str(state_dir / "sync.lock"), timeout=0):
            return run_once(root, state_dir, local_only=args.local_only)
    except Timeout:
        try:
            request_sync(state_dir, local_only_requested=args.local_only)
            return 0
        except SyncError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    except (SyncError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
