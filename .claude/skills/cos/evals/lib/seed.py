#!/usr/bin/env python3
"""Stage the current directory for one eval case: a git repo, cos set up, a batch in a state.

    python3 evals/lib/seed.py <bare|running|cost>

Runs the real CLI (no model); the batch state is reached through `cos` commands only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]
WORK = Path.cwd()
ENV = {**os.environ, "PYTHONPATH": str(SKILL / "cli" / "src"), "COS_SKILL_DIR": str(SKILL)}


def sh(*args):
    subprocess.run(args, cwd=WORK, check=True, capture_output=True, text=True)


def cos(*args):
    p = subprocess.run([sys.executable, "-m", "cos", *map(str, args)], cwd=WORK, env=ENV,
                       capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"seed: cos {' '.join(map(str, args))}: {p.stderr.strip()}")


def repo():
    if not (WORK / ".git").exists():
        sh("git", "init", "--quiet", "-b", "main")
    sh("git", "config", "user.name", "eval")
    sh("git", "config", "user.email", "eval@example.com")
    (WORK / "app.py").write_text("def login():\n    return True\n")
    (WORK / ".gitignore").write_text("__pycache__/\n.cos-fixtures/\n")
    sh("git", "add", ".")
    sh("git", "commit", "--quiet", "-m", "init")
    cos("setup")
    sh("git", "add", ".")
    sh("git", "commit", "--quiet", "-m", "cos setup")


def running():
    """Batch `night`: CR-101 ready with a PR, CR-102 working in round 2, CR-103 blocked."""
    cos("open", "night", "Fix login timeout", "Add CSV export", "Dark mode", "--slots", 2,
        "--no-worktrees", "--cos", "local_cos_eval")
    cos("foreman", "set", "local_foreman_eval")
    cos("event", "start", "--epoch", 1)
    cos("agents", "set", "CR-101", "a101", "--epoch", 1)
    cos("agents", "set", "CR-102", "a102", "--epoch", 1)
    cos("report", "CR-101", "pr-opened", "https://github.com/acme/demo/pull/40")
    cos("report", "CR-101", "ci-green")
    cos("report", "CR-101", "round-done", "r1 APPROVE")
    cos("event", "hand-back-ready", "CR-101", "https://github.com/acme/demo/pull/40",
        "--epoch", 1)
    cos("agents", "set", "CR-103", "a103", "--epoch", 1)
    cos("report", "CR-102", "round-done", "r1 FIX-REQUIRED missing header")
    cos("report", "CR-102", "round-done", "r2 in progress")
    cos("event", "hand-back-blocked", "CR-103",
        "the design system has no dark tokens; the user must choose a palette", "--epoch", 1)


def cost():
    """`running`, plus Foreman and subagent transcripts: Sonnet, $1.60 in total."""
    running()
    cfg_path = WORK / ".agents" / "cos.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["claude_projects_dir"] = ".cos-fixtures/claude-projects"
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
    cos("foreman", "transcript", "uuid-eval", "--epoch", 1)
    slug = "".join(ch if ch.isalnum() else "-" for ch in str(WORK.resolve()))
    main = WORK / ".cos-fixtures" / "claude-projects" / slug / "uuid-eval.jsonl"
    sub = main.with_suffix("") / "subagents"
    sub.mkdir(parents=True)

    def msg(mid, out):
        return json.dumps({"type": "assistant", "message": {
            "id": mid, "model": "claude-sonnet-5-5",
            "usage": {"input_tokens": 0, "output_tokens": out, "cache_read_input_tokens": 0,
                      "cache_creation": {}}}}) + "\n"

    main.write_text(msg("f1", 100_000))  # $1.00
    for agent, kind, out in (("a101", "cr-driver", 30_000), ("a102", "cr-driver", 20_000),
                             ("c9", "coder", 10_000)):  # $0.30, $0.20, $0.10
        (sub / f"agent-{agent}.jsonl").write_text(msg(agent, out))
        (sub / f"agent-{agent}.meta.json").write_text(json.dumps({"agentType": kind}))


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "bare"
    repo()
    {"bare": lambda: None, "running": running, "cost": cost}[kind]()
    print(f"seeded {kind} in {WORK}")
