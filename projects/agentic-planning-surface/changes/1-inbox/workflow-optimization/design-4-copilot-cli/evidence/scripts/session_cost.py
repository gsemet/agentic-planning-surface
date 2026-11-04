# /// script
# requires-python = ">=3.11"
# ///
"""Per-agent token and cost breakdown of one Copilot CLI session.

Reads ~/.copilot/session-state/<id>/events.jsonl and sums the persisted
`session.usage_record` events per agent (main conversation or subagent).
Cost uses the server-reported `copilotUsage.totalNanoAiu` (1 AI credit = 1e9 nano-AIU = $0.01).

Usage: uv run session_cost.py <events.jsonl> [--json]
"""

import collections
import json
import sys


def main() -> None:
    path = sys.argv[1]
    as_json = "--json" in sys.argv
    names: dict[str, str] = {}
    parents: dict[str, str] = {}
    rows: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    models: dict[str, set[str]] = collections.defaultdict(set)
    for line in open(path, encoding="utf-8"):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        agent = event.get("agentId") or "main"
        if event.get("type") == "subagent.started":
            data = event["data"]
            names[agent] = data.get("agentDisplayName") or agent
            parents[agent] = data.get("parentId") or "main"
        if event.get("type") != "session.usage_record":
            continue
        usage = event["data"]["usage"]
        row = rows[agent]
        row["calls"] += 1
        for key in ("inputTokens", "outputTokens", "cacheReadTokens", "cacheWriteTokens"):
            row[key] += usage.get(key) or 0
        row["nanoAiu"] += (usage.get("copilotUsage") or {}).get("totalNanoAiu", 0)
        models[agent].add(usage.get("model", "?"))
    out = [
        {
            "agent": names.get(agent, agent),
            "agentId": agent,
            "parent": parents.get(agent, ""),
            "models": sorted(models[agent]),
            **row,
            "usd": row["nanoAiu"] / 1e9 * 0.01,
        }
        for agent, row in sorted(rows.items(), key=lambda item: -item[1]["nanoAiu"])
    ]
    if as_json:
        print(json.dumps(out, indent=1))
        return
    header = f"{'agent':24} {'model':16} {'calls':>5} {'input':>9} {'c.read':>9} {'c.write':>8} {'output':>7} {'USD':>8}"
    print(header)
    for r in out:
        print(
            f"{r['agent'][:24]:24} {','.join(r['models'])[:16]:16} {r['calls']:5} {r['inputTokens']:9}"
            f" {r['cacheReadTokens']:9} {r['cacheWriteTokens']:8} {r['outputTokens']:7} {r['usd']:8.4f}"
        )
    print(f"TOTAL USD {sum(r['usd'] for r in out):.4f}")


if __name__ == "__main__":
    main()
