# /// script
# requires-python = ">=3.11"
# ///
"""Attribute the Foreman's turns and cost to what woke it (Opus 5.5 prices, 1-hour cache writes)."""
import json
import sys
from collections import Counter, defaultdict

PRICE = {"in": 4e-6, "w5m": 5e-6, "w1h": 8e-6, "read": 0.2e-6, "out": 20e-6}


def kind(text: str) -> str:
    if "waiting on its own background" in text:
        return "driver waiting notice"
    if "task-notification" in text or "<task-id>" in text:
        return "driver completion or stop"
    if "agent-message" in text:
        return "driver message"
    if "cross-session-message" in text:
        return "Chief of Staff message"
    if "tick" in text.lower() or "cron" in text.lower():
        return "cron tick"
    return "other"


def main(path: str, since: str) -> None:
    triggers, turns, cost, seen, last = Counter(), defaultdict(int), defaultdict(float), set(), None
    for line in open(path):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("timestamp", "") < since:
            continue
        m = d.get("message", {})
        if d.get("type") == "user":
            c = m.get("content")
            s = c if isinstance(c, str) else json.dumps(c)
            if "tool_result" in s[:200]:
                continue
            last = kind(s)
            triggers[last] += 1
        elif d.get("type") == "assistant" and m.get("usage") and m.get("id") not in seen:
            seen.add(m.get("id"))
            u, cc = m["usage"], m["usage"].get("cache_creation") or {}
            turns[last] += 1
            cost[last] += (u.get("input_tokens", 0) * PRICE["in"]
                           + cc.get("ephemeral_5m_input_tokens", 0) * PRICE["w5m"]
                           + cc.get("ephemeral_1h_input_tokens", 0) * PRICE["w1h"]
                           + u.get("cache_read_input_tokens", 0) * PRICE["read"]
                           + u.get("output_tokens", 0) * PRICE["out"])
    for k in triggers:
        print(f"{k:28s} triggers={triggers[k]:3d} turns={turns[k]:3d} "
              f"cost=${cost[k]:.3f} per trigger=${cost[k] / triggers[k]:.4f}")
    print(f"total ${sum(cost.values()):.3f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
