# /// script
# requires-python = ">=3.11"
# ///
"""Cost of the Chief of Staff's turns by what woke it: an app note on a linked session's turn,
a cross-session message, or the user. Opus 5.5 prices ($/MTok), 1-hour cache.

Usage: uv run cos_wakes.py <cos-session.jsonl> <since ISO> <until ISO>
"""
import json
import sys
from collections import Counter, defaultdict

P = (4, 5, 8, 0.20, 20)


def kind(s: str) -> str:
    if "finished a turn" in s or "side-sessions-event" in s:
        return "app note on a linked session's turn"
    if "cross-session-message" in s:
        return "cross-session message"
    return "user or other"


def main(path: str, since: str, until: str) -> None:
    wakes, turns, usd, ctx, seen, last = Counter(), Counter(), defaultdict(float), defaultdict(list), set(), None
    for line in open(path):
        d = json.loads(line)
        ts = d.get("timestamp", "")
        if not since <= ts <= until:
            continue
        m = d.get("message") or {}
        if d.get("type") == "user":
            s = m.get("content") if isinstance(m.get("content"), str) else json.dumps(m.get("content"))
            if '"tool_result"' in s[:300]:
                continue
            last = kind(s)
            wakes[last] += 1
        elif d.get("type") == "assistant" and m.get("usage") and m.get("id") not in seen and last:
            seen.add(m["id"])
            u, cc = m["usage"], m["usage"].get("cache_creation") or {}
            t = (u.get("input_tokens", 0), cc.get("ephemeral_5m_input_tokens", 0),
                 cc.get("ephemeral_1h_input_tokens", 0), u.get("cache_read_input_tokens", 0),
                 u.get("output_tokens", 0))
            turns[last] += 1
            usd[last] += sum(a * b for a, b in zip(t, P)) / 1e6
            ctx[last].append(sum(t[:4]))
    print("| Woken by | Wakes | Model calls | USD | Per wake | Context median |")
    print("| --- | ---: | ---: | ---: | ---: | ---: |")
    for k in wakes:
        c = sorted(ctx[k]) or [0]
        print(f"| {k} | {wakes[k]} | {turns[k]} | {usd[k]:.3f} | {usd[k] / wakes[k]:.3f} | {c[len(c) // 2]:,} |")


if __name__ == "__main__":
    main(*sys.argv[1:4])
