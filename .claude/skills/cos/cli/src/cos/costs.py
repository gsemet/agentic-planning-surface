"""Price a Claude Code session transcript and its subagents (design 5's claude_usage.py)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

# $/MTok: input, 5-min write, 1-h write, cache read, output (design 2, prices-corrected.md).
PRICE = {
    "opus": (4, 5, 8, 0.20, 20),
    "sonnet": (2, 2.5, 4, 0.10, 10),
    "haiku": (0.10, 0.125, 0.20, 0.01, 0.50),
    "haiku>100k": (0.50, 0.625, 1, 0.05, 2.50),
}


def projects_dir(config: dict | None = None) -> Path:
    """`COS_CLAUDE_PROJECTS`, else `claude_projects_dir` of cos.json, else ~/.claude/projects."""
    env = os.environ.get("COS_CLAUDE_PROJECTS") or (config or {}).get("claude_projects_dir")
    return Path(env).expanduser() if env else Path.home() / ".claude" / "projects"


def transcript_path(repo_root: Path, session_uuid: str, config: dict | None = None) -> Path:
    base = projects_dir(config)
    if not base.is_absolute():
        base = repo_root / base
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo_root))
    path = base / slug / f"{session_uuid}.jsonl"
    if not path.exists():  # long folder names get a shortened slug: find the uuid instead
        path = next(base.glob(f"*/{session_uuid}.jsonl"), path)
    return path


def _family(model: str, prompt: int) -> str:
    for f in ("opus", "sonnet", "haiku"):
        if f in model:
            return "haiku>100k" if f == "haiku" and prompt > 100_000 else f
    return "opus"


def usage(path: Path) -> dict:
    row = {"calls": 0, "usd": 0.0, "model": "?", "w5m": 0, "w1h": 0, "read": 0, "out": 0}
    seen = set()
    for line in path.open():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        m = d.get("message") or {}
        if d.get("type") != "assistant" or not m.get("usage") or m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        u, cc = m["usage"], m["usage"].get("cache_creation") or {}
        t = (u.get("input_tokens", 0), cc.get("ephemeral_5m_input_tokens", 0),
             cc.get("ephemeral_1h_input_tokens", 0), u.get("cache_read_input_tokens", 0),
             u.get("output_tokens", 0))
        row["model"] = m.get("model", "?")
        row["calls"] += 1
        for k, v in zip(("w5m", "w1h", "read", "out"), t[1:]):
            row[k] += v
        row["usd"] += sum(a * b for a, b in zip(t, PRICE[_family(row["model"], sum(t[:4]))])) / 1e6
    return row


def session_costs(main: Path) -> list[dict]:
    """One row for the main transcript (the Foreman) and one per subagent."""
    rows = []
    if main.exists():
        rows.append({"agent": "main", "type": "foreman", "description": "", **usage(main)})
    sub = main.with_suffix("") / "subagents"
    if sub.exists():
        for f in sorted(sub.glob("agent-*.jsonl")):
            meta_path = f.with_suffix("").with_suffix(".meta.json")
            meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
            rows.append({"agent": f.stem.removeprefix("agent-"),
                         "type": meta.get("agentType", "?"),
                         "description": meta.get("description", ""), **usage(f)})
    return rows
