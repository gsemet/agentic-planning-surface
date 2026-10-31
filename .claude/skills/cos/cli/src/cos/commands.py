"""The `cos` commands. Each returns the lines to print; errors raise CosError with an exit code."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from . import __version__, costs, forge, procs
from .decide import decide, fill_slots
from .state import (DONE, EXIT_EXTERNAL, EXIT_PRECONDITION, EXIT_USAGE, LIVE, Batch, CosError,
                    Repo, age_minutes, check_epoch, find_cr_batch, git, next_cr_number, now,
                    read_batch, resolve_batch)

DRIVER_TEMPLATES = ("cr-driver", "stack-driver", "qa-driver")
TEMPLATES = DRIVER_TEMPLATES + ("investigator", "coder", "inspector", "debugger", "verifier",
                                 "conflict-resolver")
TEMPLATE_VERSION = re.compile(r"^# cos-template: (\S+)$", re.M)


def skill_dir() -> Path:
    """The skill folder: `COS_SKILL_DIR`, else the nearest parent of this file with SKILL.md."""
    env = os.environ.get("COS_SKILL_DIR")
    if env:
        return Path(env).resolve()
    for p in Path(__file__).resolve().parents:
        if (p / "SKILL.md").exists():
            return p
    raise CosError("cannot find the cos skill folder; set COS_SKILL_DIR", EXIT_PRECONDITION)


def cos_prefix() -> str:
    return f"uv run --script {skill_dir() / 'cli' / 'cos.py'}"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "cr"


# ---- setup and preflight ----------------------------------------------------------------------

def _default_branch(root: Path) -> str:
    head = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=root, check=False)
    if head:
        return head.split("/", 1)[-1]
    return git("branch", "--show-current", cwd=root, check=False) or "main"


def _render_template(name: str, repo: Repo) -> str:
    text = (skill_dir() / "assets" / "agents" / f"{name}.md").read_text()
    model = (repo.config.get("models") or {}).get(name) or "inherit"
    return (text.replace("{{COS}}", cos_prefix())
                .replace("{{MODEL}}", model)
                .replace("{{SKILL}}", str(skill_dir()))
                .replace("{{ROOT}}", str(repo.root)))


def setup(args) -> list[str]:
    repo = Repo.find()
    out = []
    if not repo.config_path.exists():
        cfg = {**repo.config, "default_branch": _default_branch(repo.root)}
        repo.config_path.parent.mkdir(parents=True, exist_ok=True)
        repo.config_path.write_text(json.dumps(cfg, indent=2) + "\n")
        out.append(f"wrote {repo.config_path.relative_to(repo.root)} "
                   f"(default branch {cfg['default_branch']})")
        repo = Repo.find()
    (repo.batches).mkdir(parents=True, exist_ok=True)
    agents = repo.root / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    installed_path = repo.root / ".agents" / "cos-installed.json"
    installed = json.loads(installed_path.read_text()) if installed_path.exists() else {}
    for name in TEMPLATES:
        target = agents / f"{name}.md"
        text = _render_template(name, repo)
        if target.exists() and target.read_text() == text:
            installed[name] = _digest(text)
            continue
        edited = target.exists() and _digest(target.read_text()) != installed.get(name)
        if edited and not args.force:
            out.append(f"kept .claude/agents/{name}.md (edited locally; --force to replace)")
            continue
        target.write_text(text)
        installed[name] = _digest(text)
        out.append(f"installed .claude/agents/{name}.md")
    installed_path.write_text(json.dumps(installed, indent=2) + "\n")
    out.append("setup done" if out else "setup: nothing to change")
    out.append("restart the Desktop session if agent files changed: agents load at start")
    return out


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _version_of(path: Path) -> str | None:
    m = TEMPLATE_VERSION.search(path.read_text())
    return m.group(1) if m else None


def _skill_version() -> str | None:
    m = re.search(r"^cos-version: (\S+)$", (skill_dir() / "SKILL.md").read_text(), re.M)
    return m.group(1) if m else None


def preflight(args) -> tuple[list[str], int]:
    lines, ok = [], True

    def check(tag: str, passed: bool, good: str, bad: str):
        nonlocal ok
        ok &= passed
        lines.append(f"{tag} {'ok  ' if passed else 'FAIL'} {good if passed else bad}")

    entry = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "")
    check("P1", entry == "claude-desktop", "host is Claude Desktop",
          f"host is {entry or 'unknown'} (CLAUDE_CODE_ENTRYPOINT), not claude-desktop")
    try:
        repo = Repo.find(Path(os.getcwd()))
    except CosError as e:
        repo = None
        check("P6", False, "", str(e))
    if repo:
        agents = repo.root / ".claude" / "agents"
        missing = [n for n in TEMPLATES if not (agents / f"{n}.md").exists()]
        stale = [n for n in TEMPLATES if n not in missing
                 and _version_of(agents / f"{n}.md") != __version__]
        no_ttl = [n for n in DRIVER_TEMPLATES if n not in missing
                  and "cacheTtl: 1h" not in (agents / f"{n}.md").read_text()]
        problems = ([f"missing {', '.join(missing)}"] if missing else []) + \
                   ([f"old template {', '.join(stale)}"] if stale else []) + \
                   ([f"no 1h cache in {', '.join(no_ttl)}"] if no_ttl else [])
        check("P4", not problems, "agent files installed and current",
              "; ".join(problems) + " (run `cos setup`, then restart the session)")
    has_uv = shutil.which("uv") is not None
    sv = _skill_version()
    check("P5", has_uv and sv == __version__, f"cos {__version__}, uv found",
          f"uv {'found' if has_uv else 'missing'}; CLI {__version__}, SKILL.md {sv}")
    if repo:
        top = Path(git("rev-parse", "--show-toplevel", check=False) or ".").resolve()
        configured = repo.config_path.exists() and repo.changes.exists()
        check("P6", top == repo.root.resolve() and configured,
              f"in the main checkout of {repo.root.name}, cos configured",
              ("not configured: run `cos setup`" if not configured
               else f"session folder {top} is not the repository root {repo.root}"))
        gitdir = Path(git("rev-parse", "--path-format=absolute", "--git-dir", check=False)
                      or ".").resolve()
        common = (repo.root / ".git").resolve()
        check("P7", gitdir == common, "not a linked worktree",
              "this session runs in a linked worktree: detach_session would refuse the Foreman")
    lines.append("P2, P3 and 'not unattended' are the Chief of Staff's own checks")
    lines.append("preflight passed" if ok else "preflight FAILED: start nothing")
    return lines, 0 if ok else EXIT_PRECONDITION


# ---- batches and CRs --------------------------------------------------------------------------

def _base_ref(repo: Repo) -> str:
    remote, branch = repo.config["remote"], repo.config["default_branch"]
    if git("remote", cwd=repo.root, check=False).split().count(remote):
        git("fetch", "--quiet", remote, branch, cwd=repo.root, check=False)
        if git("rev-parse", "--verify", "--quiet", f"{remote}/{branch}", cwd=repo.root,
               check=False):
            return f"{remote}/{branch}"
    return branch


def add_cr(b: Batch, item: str, qa: bool = False) -> dict:
    """Create one CR: its folder, task, STATE.md, branch and worktree; queued."""
    repo = b.repo
    text, title = item, item
    path = Path(item[1:]) if item.startswith("@") else None
    if path is not None:
        if not path.is_absolute():
            path = repo.root / path
        if not path.exists():
            raise CosError(f"backlog item not found: {path}", EXIT_USAGE)
        text = path.read_text()
        title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.strip()),
                     path.stem)
    cr_id = f"CR-{next_cr_number(repo)}"
    cdir = b.dir / "crs" / cr_id
    (cdir / "scratch").mkdir(parents=True, exist_ok=True)
    (cdir / "task.md").write_text(text if text.endswith("\n") else text + "\n")
    branch = f"cos/{b.id}/{cr_id.lower()}-{_slug(title)}"
    worktree = None
    if not b.data.get("no_worktrees"):
        worktree = repo.worktrees / f"{b.id}-{cr_id}"
        worktree.parent.mkdir(parents=True, exist_ok=True)
        git("worktree", "add", "--quiet", "-b", branch, str(worktree), _base_ref(repo),
            cwd=repo.root)
    order = max((c["order"] for c in b.data["crs"]), default=0) + 1
    c = {"id": cr_id, "title": title, "item": item, "status": "queued", "order": order,
         "round": 0, "qa": qa, "qa_done": False, "agent": None, "pr": None, "ci": None,
         "branch": branch, "worktree": str(worktree) if worktree else None, "pgids": [], "pids": [],
         "notes": [], "resumes": 0, "updated": now()}
    (cdir / "STATE.md").write_text(
        f"# {cr_id}: {title}\n\n- batch: {b.id}\n- branch: `{branch}`\n"
        f"- worktree: `{c['worktree']}`\n- status: queued\n")
    b.data["crs"].append(c)
    b.log("add", cr_id, title=title)
    return c


def open_batch(args) -> list[str]:
    repo = Repo.find()
    if not repo.config_path.exists():
        raise CosError("cos is not set up here: run `cos setup`")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", args.batch):
        raise CosError("batch id: lowercase letters, digits and hyphens", EXIT_USAGE)
    qa_all = args.qa == "all"
    qa_idx = set() if qa_all or not args.qa else {int(i) for i in args.qa.split(",")}
    data = {"id": args.batch, "version": __version__, "created": now(), "status": "open",
            "mode": "stack" if args.stack else "parallel", "slots": args.slots,
            "budget_usd": args.budget, "spent_usd": 0.0, "paused": False,
            "foreman": None, "foreman_epoch": 0, "foreman_transcript": None, "cos": args.cos,
            "no_worktrees": args.no_worktrees, "stack_live": False, "heartbeat": None,
            "orders": [], "crs": []}
    with Batch(repo, args.batch, actor="cos", create=data) as b:
        for i, item in enumerate(args.items, 1):
            add_cr(b, item, qa=qa_all or i in qa_idx)
        brief = b.dir / "brief.md"
        brief.write_text(f"# Batch {args.batch}\n\n- Mode: {data['mode']}. Slots: {args.slots}. "
                         f"Budget: {args.budget or 'none'}.\n- CRs, in order:\n" +
                         "".join(f"  - {c['id']}: {c['title']}{' (QA)' if c['qa'] else ''}\n"
                                 for c in b.data["crs"]) +
                         "- Models (optional, per role or per CR; empty = agent file default):\n"
                         "- Night policy card: one extra round per CR; a red PR goes to the top.\n"
                         "- Autonomous decisions:\n- Questions to bring back:\n")
        b.log("open", None, crs=[c["id"] for c in b.data["crs"]])
    lines = [f"opened {args.batch}: {len(args.items)} CRs, {args.slots} slots, {data['mode']}"]
    lines += [f"{c['id']} {c['title'][:60]}" for c in b.data["crs"]]
    lines.append(f"brief: {brief.relative_to(repo.root)}")
    return lines


def add(args) -> list[str]:
    repo = Repo.find()
    with Batch(repo, resolve_batch(repo, args.batch), actor="cos") as b:
        c = add_cr(b, args.item, qa=args.qa)
    return [f"added {c['id']} {c['title'][:60]} (queued)"]


# ---- the Foreman and orders -------------------------------------------------------------------

def foreman(args) -> list[str]:
    repo = Repo.find()
    batch = resolve_batch(repo, args.batch)
    if args.action == "get":
        d = read_batch(repo, batch)
        return [f"{d.get('foreman') or 'none'} epoch {d.get('foreman_epoch', 0)}"]
    with Batch(repo, batch, actor="cos" if args.action == "set" else "foreman") as b:
        if args.action == "set":
            if not args.value:
                raise CosError("foreman set <session-id>", EXIT_USAGE)
            b.data["foreman"] = args.value
            b.data["foreman_epoch"] = b.data.get("foreman_epoch", 0) + 1
            b.data["foreman_transcript"] = None
            b.log("foreman", None, session=args.value, epoch=b.data["foreman_epoch"])
            return [f"foreman {args.value} epoch {b.data['foreman_epoch']}"]
        check_epoch(b, args.epoch)
        b.data["foreman_transcript"] = args.value
        b.log("foreman-transcript", None, transcript=args.value)
        return [f"transcript {args.value}"]


ORDER_KINDS = {"add", "drop", "first", "change", "merged", "pause", "resume"}


def order(args) -> list[str]:
    if args.kind not in ORDER_KINDS:
        raise CosError(f"order kind: one of {', '.join(sorted(ORDER_KINDS))}", EXIT_USAGE)
    repo = Repo.find()
    with Batch(repo, resolve_batch(repo, args.batch), actor="cos") as b:
        oid = f"O-{len(b.data['orders']) + 1}"
        b.data["orders"].append({"id": oid, "kind": args.kind, "cr": args.cr or "-",
                                 "note": args.note or "", "sent": now(), "done": None})
        b.log("order", None if args.cr in (None, "-") else args.cr, order=oid, order_kind=args.kind)
    target = f" {args.cr}" if args.cr and args.cr != "-" else ""
    note = f" {args.note}" if args.note else ""
    return [f"[cos→foreman] order {oid} {args.kind}{target}{note}"]


def event(args) -> list[str]:
    repo = Repo.find()
    batch = resolve_batch(repo, args.batch)
    with Batch(repo, batch, actor="foreman") as b:
        check_epoch(b, args.epoch)
        kind, cr, note = args.kind, args.cr, args.note or ""
        if args.order:
            o = next((x for x in b.data["orders"] if x["id"] == args.order), None)
            if o is None:
                raise CosError(f"unknown order {args.order}", EXIT_USAGE)
            kind, cr, note = f"order-{o['kind']}", o["cr"], note or o["note"]
        if cr not in ("-", "stack") and not cr.startswith("qa:"):
            b.cr(cr)
        b.data["heartbeat"] = now()
        return decide(b, cr, kind, note, order=args.order)


def heartbeat(args) -> list[str]:
    repo = Repo.find()
    with Batch(repo, resolve_batch(repo, args.batch), actor="foreman") as b:
        check_epoch(b, args.epoch)
        b.data["heartbeat"] = now()
        b.log("heartbeat", None)
        pending = [o for o in b.data["orders"] if not o["done"]]
        live = [c for c in b.data["crs"] if c["status"] in LIVE]
        ages = [age_minutes(c.get("updated")) or 0 for c in live]
    lines = [f"heartbeat {b.id}: {len(live)} live, {len(pending)} orders pending"]
    if pending:
        lines.append(f"oldest pending order {pending[0]['id']} "
                     f"{age_minutes(pending[0]['sent']):.0f} min")
    if ages:
        lines.append(f"oldest silent Driver {max(ages):.0f} min")
    return lines


# ---- state for every role ---------------------------------------------------------------------

def status(args) -> list[str]:
    repo = Repo.find()
    d = read_batch(repo, resolve_batch(repo, args.batch))
    if args.json:
        return [json.dumps(d, indent=2)]
    hb = age_minutes(d.get("heartbeat"))
    lines = [f"{d['id']} {d['status']} {d['mode']} slots {d['slots']} "
             f"foreman {d.get('foreman') or 'none'} e{d.get('foreman_epoch', 0)} "
             f"heartbeat {'never' if hb is None else f'{hb:.0f} min'}"
             f"{' PAUSED' if d.get('paused') else ''} spent ${d.get('spent_usd', 0):.2f}"]
    for c in sorted(d["crs"], key=lambda c: c["order"]):
        row = f"{c['id']} {c['status']} r{c['round']} {c.get('pr') or '-'} ci {c.get('ci') or '-'}"
        if c["status"] == "blocked" and c.get("blocked_reason"):
            row += f" | blocked: {c['blocked_reason'][:70]}"
        elif args.notes and c.get("notes"):
            row += f" | {c['notes'][-1][:60]}"
        lines.append(row)
    pending = sum(1 for o in d.get("orders", []) if not o["done"])
    if pending:
        lines.append(f"{pending} orders pending")
    return lines


def agents(args) -> list[str]:
    repo = Repo.find()
    batch = find_cr_batch(repo, args.cr.removeprefix("qa:"), args.batch) \
        if args.cr != "stack" else resolve_batch(repo, args.batch)
    if args.action == "get":
        d = read_batch(repo, batch)
        if args.cr == "stack":
            return [d.get("stack_agent") or "none"]
        c = next(x for x in d["crs"] if x["id"] == args.cr.removeprefix("qa:"))
        return [(c.get("qa_agent") if args.cr.startswith("qa:") else c.get("agent")) or "none"]
    with Batch(repo, batch, actor="foreman") as b:
        check_epoch(b, args.epoch)
        if args.cr == "stack":
            b.data["stack_agent"] = args.agent
        else:
            c = b.cr(args.cr.removeprefix("qa:"))
            b.touch(c, **({"qa_agent": args.agent} if args.cr.startswith("qa:")
                          else {"agent": args.agent}))
        b.log("agent", args.cr, agent=args.agent)
    return [f"{args.cr} → {args.agent}"]


REPORT_KINDS = {"pr-opened", "ci-green", "ci-red", "ci-red-known", "round-done", "note"}


def report(args) -> list[str]:
    if args.kind not in REPORT_KINDS:
        raise CosError(f"report kind: one of {', '.join(sorted(REPORT_KINDS))}", EXIT_USAGE)
    repo = Repo.find()
    with Batch(repo, find_cr_batch(repo, args.cr, args.batch), actor="driver") as b:
        c = b.cr(args.cr)
        note = args.note or ""
        if args.kind == "pr-opened":
            b.touch(c, pr=note.split()[0] if note else c.get("pr"))
        elif args.kind.startswith("ci-"):
            b.touch(c, ci=args.kind.removeprefix("ci-"))
        elif args.kind == "round-done":
            b.touch(c, round=c.get("round", 0) + 1)
        else:
            b.touch(c)
        if note and args.kind != "pr-opened":
            c.setdefault("notes", []).append(f"{args.kind}: {note}")
        b.log("report", args.cr, report=args.kind, note=note)
    return ["ok"]


# ---- work in the CR worktree ------------------------------------------------------------------

def _worktree(c: dict) -> Path:
    if not c.get("worktree") or not Path(c["worktree"]).exists():
        raise CosError(f"{c['id']} has no worktree", EXIT_PRECONDITION)
    return Path(c["worktree"])


def _track_pgid(repo: Repo, batch: str, cr: str, pgid: int, add: bool, key: str = "pgids") -> None:
    """Record a process group (gates) or a pid (`cos wait`) so `cos cancel` can stop it."""
    with Batch(repo, batch, actor="cli") as b:
        c = b.cr(cr)
        pg = set(c.get(key, []))
        (pg.add if add else pg.discard)(pgid)
        c[key] = sorted(pg)
        b.log(f"{key[:-1]}-add" if add else f"{key[:-1]}-done", cr, **{key[:-1]: pgid})


def gate(args) -> tuple[list[str], int]:
    repo = Repo.find()
    batch = find_cr_batch(repo, args.cr, args.batch)
    c = next(x for x in read_batch(repo, batch)["crs"] if x["id"] == args.cr)
    wt = _worktree(c)
    cmds = repo.config["gates"]["long" if args.long else "fast"]
    if not cmds:
        return [f"no {'long' if args.long else 'fast'} gates configured in .agents/cos.json"], 0
    logdir = repo.batch_dir(batch) / "crs" / args.cr / "scratch" / "gates"
    logdir.mkdir(parents=True, exist_ok=True)
    log = logdir / f"{time.strftime('%Y%m%d-%H%M%S')}-{'long' if args.long else 'fast'}.log"
    with open(log, "w") as f:
        for cmd in cmds:
            f.write(f"$ {cmd}\n")
            f.flush()
            p = subprocess.Popen(cmd, shell=True, cwd=wt, stdout=f, stderr=subprocess.STDOUT,
                                 start_new_session=True)
            _track_pgid(repo, batch, args.cr, p.pid, True)
            try:
                rc = p.wait()
            finally:
                _track_pgid(repo, batch, args.cr, p.pid, False)
            if rc != 0:
                f.flush()
                tail = log.read_text().splitlines()[-8:]
                return ([f"FAIL {cmd} (exit {rc}); log {log.relative_to(repo.root)}"] + tail,
                        EXIT_EXTERNAL)
    return [f"pass {len(cmds)} {'long' if args.long else 'fast'} gates; "
            f"log {log.relative_to(repo.root)}"], 0


def wait(args) -> tuple[list[str], int]:
    if args.what != "ci":
        raise CosError("wait: only `ci` is supported; run long suites with `cos gate --long`",
                       EXIT_USAGE)
    repo = Repo.find()
    batch = find_cr_batch(repo, args.cr, args.batch)
    c = next(x for x in read_batch(repo, batch)["crs"] if x["id"] == args.cr)
    if not c.get("pr"):
        raise CosError(f"{args.cr} has no PR yet", EXIT_PRECONDITION)
    interval = float(os.environ.get("COS_WAIT_INTERVAL", "60"))
    pid = os.getpid()  # our own pid only: our process group may hold the Driver's shell
    _track_pgid(repo, batch, args.cr, pid, True, "pids")
    deadline = time.monotonic() + args.max
    try:
        while True:
            checks = forge.pr_checks(c.get("worktree") or repo.root, repo.config, c["pr"])
            pending = [x for x in checks if x.get("bucket") == "pending"]
            if checks and not pending:
                failed = [x["name"] for x in checks if x.get("bucket") in {"fail", "cancel"}]
                result = "fail" if failed else "pass"
                break
            if time.monotonic() >= deadline:
                result, failed = "timeout", []
                break
            time.sleep(interval)
    finally:
        _track_pgid(repo, batch, args.cr, pid, False, "pids")
    with Batch(repo, batch, actor="driver") as b:
        b.touch(b.cr(args.cr), ci={"pass": "green", "fail": "red"}.get(result, "pending"))
        b.log("wait", args.cr, result=result)
    lines = [f"ci {result} {c['pr']}"] + ([f"failed: {', '.join(failed)}"] if failed else [])
    return lines, 0 if result == "pass" else (EXIT_EXTERNAL if result == "fail" else 0)


def ci_classify(args) -> list[str]:
    repo = Repo.find()
    batch = find_cr_batch(repo, args.cr, args.batch)
    c = next(x for x in read_batch(repo, batch)["crs"] if x["id"] == args.cr)
    if not c.get("pr"):
        raise CosError(f"{args.cr} has no PR yet", EXIT_PRECONDITION)
    cwd = c.get("worktree") or repo.root
    checks = forge.pr_checks(cwd, repo.config, c["pr"])
    red = forge.main_failures(cwd, repo.config, repo.config["default_branch"])
    logs = {x["name"]: forge.failed_log(cwd, repo.config, x.get("link", ""))
            for x in checks if x.get("bucket") == "fail"}
    tag = forge.classify(checks, red, logs)
    with Batch(repo, batch, actor="driver") as b:
        b.log("ci-classify", args.cr, tag=tag)
    failed = [x for x in checks if x.get("bucket") in {"fail", "cancel"}]
    return [tag] + [f"{x['name']} {x.get('link', '')}" for x in failed[:5]]


def _stack_base(b_data: dict, c: dict, repo: Repo) -> str:
    """In stack mode, a CR sits on the previous live CR of the stack; else on the default."""
    default = repo.config["default_branch"]
    if b_data["mode"] != "stack":
        return default
    order = [x for x in sorted(b_data["crs"], key=lambda x: x["order"])
             if x["status"] not in {"cancelled", "merged", "landed"}]
    ids = [x["id"] for x in order]
    i = ids.index(c["id"]) if c["id"] in ids else 0
    return order[i - 1]["branch"] if i > 0 else default


def ship(args) -> list[str]:
    repo = Repo.find()
    batch = find_cr_batch(repo, args.cr, args.batch)
    d = read_batch(repo, batch)
    c = next(x for x in d["crs"] if x["id"] == args.cr)
    wt = _worktree(c)
    dirty = git("status", "--porcelain", "--untracked-files=no", cwd=wt)
    if dirty:
        raise CosError(f"{args.cr}: uncommitted changes in the worktree; commit them first: "
                       f"{' '.join(ln.split(maxsplit=1)[-1] for ln in dirty.splitlines()[:5])}")
    remote = repo.config["remote"]
    if remote not in git("remote", cwd=wt).split():
        raise CosError(f"no remote {remote!r}", EXIT_EXTERNAL)
    base = _stack_base(d, c, repo)
    git("fetch", "--quiet", remote, cwd=wt)
    onto = f"{remote}/{base}" if base == repo.config["default_branch"] else base
    rb = subprocess.run(["git", "rebase", onto], cwd=wt, capture_output=True, text=True,
                        env={**os.environ, "GIT_EDITOR": "true"})
    if rb.returncode != 0:
        subprocess.run(["git", "rebase", "--abort"], cwd=wt, capture_output=True)
        raise CosError(f"{args.cr}: rebase on {onto} failed; aborted: "
                       f"{rb.stdout.strip()[-200:]}", EXIT_EXTERNAL)
    git("push", "--quiet", "--force-with-lease", "-u", remote, c["branch"], cwd=wt)
    body = repo.batch_dir(batch) / "crs" / args.cr / "pr-body.md"
    if not body.exists():
        raise CosError(f"write {body.relative_to(repo.root)} before `cos ship`")
    if c.get("pr"):
        forge.pr_edit(wt, repo.config, c["pr"], body_file=str(body), base=base)
        link, verb = c["pr"], "updated"
    else:
        link = forge.pr_create(wt, repo.config, base, c["branch"], args.title or c["title"],
                               str(body))
        verb = "opened"
    with Batch(repo, batch, actor="driver") as b:
        b.touch(b.cr(args.cr), pr=link, ci="pending")
        b.log("ship", args.cr, pr=link, base=base)
    return [f"{verb} {link} (base {base})"]


def stack(args) -> list[str]:
    repo = Repo.find()
    batch = resolve_batch(repo, args.batch)
    if args.action == "order":
        with Batch(repo, batch, actor="stack") as b:
            for i, cr in enumerate(args.crs, 1):
                b.touch(b.cr(cr), order=i)
            b.log("stack-order", None, crs=args.crs)
        return [f"stack order: {' → '.join(args.crs)}"]
    d = read_batch(repo, batch)
    if d["mode"] != "stack":
        raise CosError(f"batch {batch} is not a stack")
    affected = []
    for c in sorted(d["crs"], key=lambda x: x["order"]):
        if c["status"] in {"cancelled", "merged", "landed"} or not c.get("pr"):
            continue
        ship(type("A", (), {"cr": c["id"], "batch": batch, "title": None})())
        affected.append(c["id"])
        d = read_batch(repo, batch)
    with Batch(repo, batch, actor="stack") as b:
        b.log("restack", None, crs=affected)
    return [f"restacked {len(affected)}: {' '.join(affected) or 'none'}"]


def qa(args) -> list[str]:
    repo = Repo.find()
    with Batch(repo, find_cr_batch(repo, args.cr, args.batch), actor="qa") as b:
        c = b.cr(args.cr)
        if args.action == "start":
            b.touch(c, status="qa")
            b.log("qa-start", args.cr)
            return ["ok"]
        n = 0
        if args.findings:
            text = Path(args.findings).read_text()
            n = sum(1 for ln in text.splitlines() if ln.lstrip().startswith(("- ", "* ")))
            c["qa_findings"] = str(Path(args.findings).resolve())
        b.touch(c)
        b.log("qa-done", args.cr, findings=n)
    return [f"qa done {args.cr}: {n} findings; tell the Foreman: "
            f"[qa {args.cr}→foreman] qa done {args.cr} {n} findings"]


def cancel(args) -> list[str]:
    repo = Repo.find()
    with Batch(repo, find_cr_batch(repo, args.cr, args.batch), actor="foreman") as b:
        check_epoch(b, args.epoch)
        c = b.cr(args.cr)
        killed = []
        for pg in c.get("pgids", []):
            try:
                os.killpg(pg, signal.SIGTERM)
                killed.append(f"pg{pg}")
            except (ProcessLookupError, PermissionError):
                pass
        killed += [str(p) for p in procs.stop(c.get("pids", []))]
        if c.get("worktree") and Path(c["worktree"]).exists():
            killed += [str(p) for p in procs.stop(procs.find(Path(c["worktree"])))]
        b.touch(c, status="cancelled", agent=None, pgids=[], pids=[])
        b.log("cancel", args.cr, killed=killed)
        actions = fill_slots(b)
    return [f"cancelled {args.cr}; stopped {len(killed)}: {' '.join(killed) or 'none'}"] + actions


def land(args) -> list[str]:
    repo = Repo.find()
    batch = resolve_batch(repo, args.batch)
    with Batch(repo, batch, actor="foreman") as b:
        check_epoch(b, args.epoch)
        live = [c["id"] for c in b.data["crs"] if c["status"] in LIVE]
        pending = [o["id"] for o in b.data["orders"] if not o["done"]]
        queued = [c["id"] for c in b.data["crs"] if c["status"] == "queued"]
        open_ = [c["id"] for c in b.data["crs"] if c["status"] in {"ready", "blocked"}]
        if live or pending or queued or open_ or b.data.get("stack_live"):
            raise CosError(f"cannot land {batch}: live {live or '-'}, queued {queued or '-'}, "
                           f"not merged {open_ or '-'}, orders pending {pending or '-'}, "
                           f"stack driver {'live' if b.data.get('stack_live') else 'done'}")
        cleaned = []
        for c in b.data["crs"]:
            if c["status"] in {"merged", "cancelled"} and c.get("worktree"):
                git("worktree", "remove", "--force", c["worktree"], cwd=repo.root, check=False)
                git("branch", "-D", c["branch"], cwd=repo.root, check=False)
                cleaned.append(c["id"])
        rows = "".join(f"| {c['id']} | {c['title']} | {c['status']} | {c.get('pr') or '-'} | "
                       f"{c['round']} |\n" for c in sorted(b.data["crs"], key=lambda c: c["order"]))
        report_path = b.dir / "report.md"
        report_path.write_text(
            f"# Batch {batch}: report\n\n- Landed: {now()}\n- Spent: ${b.data.get('spent_usd', 0):.2f}"
            f"\n\n| CR | Title | Status | PR | Rounds |\n| --- | --- | --- | --- | ---: |\n{rows}")
        b.data["status"] = "landed"
        b.log("land", None, cleaned=cleaned)
    return [f"landed {batch}: cleaned {len(cleaned)} worktrees",
            f"report: {report_path.relative_to(repo.root)}"]


def cost(args) -> list[str]:
    repo = Repo.find()
    batch = resolve_batch(repo, args.batch)
    d = read_batch(repo, batch)
    uuid = args.transcript or d.get("foreman_transcript")
    if not uuid:
        raise CosError("no Foreman transcript recorded: the Foreman runs "
                       "`cos foreman transcript $CLAUDE_CODE_SESSION_ID`")
    rows = costs.session_costs(costs.transcript_path(repo.root, uuid, repo.config))
    if not rows:
        raise CosError(f"transcript {uuid} not found under {costs.projects_dir(repo.config)}",
                       EXIT_EXTERNAL)
    agent_cr = {}
    for c in d["crs"]:
        if c.get("agent"):
            agent_cr[c["agent"]] = c["id"]
        if c.get("qa_agent"):
            agent_cr[c["qa_agent"]] = c["id"]
    total = sum(r["usd"] for r in rows)
    if args.update:
        with Batch(repo, batch, actor="foreman") as b:
            b.data["spent_usd"] = round(total, 4)
            b.log("cost", None, usd=total)
    groups: dict[str, list] = defaultdict(lambda: [0, 0.0])
    for r in rows:
        if args.by == "cr":
            key = "foreman" if r["agent"] == "main" else agent_cr.get(r["agent"], "other")
        else:
            key = r["type"]
        groups[key][0] += r["calls"]
        groups[key][1] += r["usd"]
    lines = [f"{batch}: ${total:.3f} over {sum(r['calls'] for r in rows)} model calls"]
    lines += [f"{k}: ${v[1]:.3f} ({v[0]} calls)"
              for k, v in sorted(groups.items(), key=lambda kv: -kv[1][1])]
    return lines
