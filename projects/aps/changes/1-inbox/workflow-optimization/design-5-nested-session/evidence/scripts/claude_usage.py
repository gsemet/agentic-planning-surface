# /// script
# requires-python = ">=3.11"
# ///
"""Per-agent tokens, cache TTL and cost of one Claude Code session and its subagents.

Reads <session>.jsonl and <session>/subagents/*.jsonl. Prices from design 2's
prices-corrected.md ($/MTok: input, 5-min write, 1-h write, cache read, output).

Usage: uv run claude_usage.py <session.jsonl> [--since <ISO timestamp>]
"""
import json
import sys
from pathlib import Path

PRICE = {
    "opus": (4, 5, 8, 0.20, 20),
    "sonnet": (2, 2.5, 4, 0.10, 10),
    "haiku": (0.10, 0.125, 0.20, 0.01, 0.50),
    "haiku>100k": (0.50, 0.625, 1, 0.05, 2.50),
}


def family(model: str, prompt: int) -> str:
    for f in ("opus", "sonnet", "haiku"):
        if f in model:
            return "haiku>100k" if f == "haiku" and prompt > 100_000 else f
    return "opus"


def usage(path: Path, since: str) -> dict:
    row = {"turns": 0, "in": 0, "w5m": 0, "w1h": 0, "read": 0, "out": 0, "usd": 0.0, "model": "?"}
    seen = set()
    for line in path.open():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        m = d.get("message") or {}
        if d.get("type") != "assistant" or not m.get("usage") or d.get("timestamp", "") < since:
            continue
        if m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        u, cc = m["usage"], m["usage"].get("cache_creation") or {}
        t = (u.get("input_tokens", 0), cc.get("ephemeral_5m_input_tokens", 0),
             cc.get("ephemeral_1h_input_tokens", 0), u.get("cache_read_input_tokens", 0),
             u.get("output_tokens", 0))
        p = PRICE[family(m.get("model", ""), sum(t[:4]))]
        row["model"] = m.get("model", "?")
        row["turns"] += 1
        for k, v in zip(("in", "w5m", "w1h", "read", "out"), t):
            row[k] += v
        row["usd"] += sum(a * b for a, b in zip(t, p)) / 1e6
    return row


def main() -> None:
    main_path = Path(sys.argv[1])
    since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else ""
    paths = [main_path] + sorted((main_path.with_suffix("") / "subagents").glob("*.jsonl"))
    total = 0.0
    print("| Agent | Model | Turns | Input | 5-min writes | 1-h writes | Reads | Output | USD |")
    print("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for p in paths:
        r = usage(p, since)
        if not r["turns"]:
            continue
        total += r["usd"]
        name = "main" if p == main_path else p.stem.removeprefix("agent-")[:10]
        print(f"| {name} | {r['model']} | {r['turns']} | {r['in']:,} | {r['w5m']:,} | {r['w1h']:,} "
              f"| {r['read']:,} | {r['out']:,} | {r['usd']:.3f} |")
    print(f"| **Total** | | | | | | | | **{total:.3f}** |")


if __name__ == "__main__":
    main()
