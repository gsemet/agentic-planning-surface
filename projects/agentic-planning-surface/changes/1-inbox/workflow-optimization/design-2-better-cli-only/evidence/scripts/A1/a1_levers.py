"""Items 3-6, 8: sequential lever simulation per role and scope, low/high assumptions."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_sim import *
rows, byid = load_all(); calibrate(rows)
WEEK = 7 / 7.61
ORCHROWS = [r for r in rows if r["role"] in ORCH]
def total(rs, lv, ttl=300, fam=None, cap=None, mode="rotate"):
    out = collections.Counter(); rot = 0; nk = 0
    for r in rs:
        c, k, ro = simulate(r, lv, ttl, fam, cap, mode); out[r["role"]] += c; rot += ro; nk += k
    return out, rot, nk

def path(name, steps, rs):
    print(f"\n### {name}")
    print("| Step (cumulative) | " + " | ".join(D2NAME[ro] for ro in ORCH) + " | Total | Δ vs previous | turns | rotations |")
    print("|" + "---|" * (len(ORCH) + 5))
    prev = None; res = []
    for label, lv, ttl, fam, cap, mode in steps:
        o, rot, nk = total(rs, lv, ttl, fam, cap, mode); T = sum(o.values())
        print(f"| {label} | " + " | ".join(f"{o[ro]:.2f}" for ro in ORCH) + f" | {T:.2f} | {'' if prev is None else f'{T-prev:+.2f}'} | {nk} | {rot} |")
        prev = T; res.append((label, T, o))
    return res

LOW = {"waits": "low", "mech": "low", "handback": 600, "status": 800}
HIGH = {"waits": "high", "mech": "high", "handback": 300, "status": 400}
for scope_name, rs in [("all orchestration agents", ORCHROWS),
                       ("factory scope (runs 1-5 + pre-run-1 batches)", [r for r in ORCHROWS if scope(r) != "other workstreams"]),
                       ("runs 1-5 only", [r for r in ORCHROWS if scope(r) == "runs 1-5"])]:
    real_ = sum(real(r) for r in rs)
    print(f"\n## Scope: {scope_name} — real ${real_:.2f} in window, ${real_*WEEK:.2f}/week")
    # rotation/compaction cap sweep after L2-L4ab (high and low)
    for nm, lv in (("low", LOW), ("high", HIGH)):
        print(f"\ncap sweep after L2+L3+L4ab {nm}:", end=" ")
        for cap in (None, 60e3, 100e3, 150e3):
            for mode in (("rotate", "compact") if cap else ("rotate",)):
                for ttl in (300, 3600):
                    o, rot, _ = total(rs, lv, ttl, None, cap, mode)
                    print(f"[cap {int(cap/1e3) if cap else '-'}k {mode[:3]} ttl {ttl//60}m: ${sum(o.values()):.2f} rot {rot}]", end=" ")
        print()
    low = path(f"LOW path — {scope_name}", [
        ("0 sim baseline (5-min TTL, current models)", {}, 300, None, None, "rotate"),
        ("+L2 waits outside LLM (polls/sleeps only)", {"waits": "low"}, 300, None, None, "rotate"),
        ("+L3 crf collapses git/gh + status-write runs >=3", {"waits": "low", "mech": "low"}, 300, None, None, "rotate"),
        ("+L4a/b hand-back cap 600 tok, status cap 800 tok", LOW, 300, None, None, "rotate"),
        ("+L4c rotation at 150k", LOW, 300, None, 150e3, "rotate"),
        ("+L5 1-h TTL for these roles", LOW, 3600, None, 150e3, "rotate"),
        ("+L6 Sonnet for all (Opus drivers/foremen -> Sonnet)", LOW, 3600, "sonnet", 150e3, "rotate"),
    ], rs)
    high = path(f"HIGH path — {scope_name}", [
        ("0 sim baseline (5-min TTL, current models)", {}, 300, None, None, "rotate"),
        ("+L2 waits outside LLM (+ idle ticks, CI checks)", {"waits": "high"}, 300, None, None, "rotate"),
        ("+L3 crf collapses all mechanical runs >=2", {"waits": "high", "mech": "high"}, 300, None, None, "rotate"),
        ("+L4a/b hand-back cap 300 tok, crf status 400 tok", HIGH, 300, None, None, "rotate"),
        ("+L4c rotation at 100k", HIGH, 300, None, 100e3, "rotate"),
        ("+L5 1-h TTL for these roles", HIGH, 3600, None, 100e3, "rotate"),
        ("+L6 Sonnet for all", HIGH, 3600, "sonnet", 100e3, "rotate"),
        ("(alt L6) Haiku for all (rotation keeps ctx < 200k)", HIGH, 3600, "haiku", 100e3, "rotate"),
    ], rs)
    # TTL alone today, and model alone today
    o5, _, _ = total(rs, {}, 300); o1, _, _ = total(rs, {}, 3600)
    print(f"\nTTL alone (no other lever): 5-min ${sum(o5.values()):.2f} vs 1-h ${sum(o1.values()):.2f}; per role 1h-5m: " + ", ".join(f"{ro} {o1[ro]-o5[ro]:+.2f}" for ro in ORCH))
    for fam in ("sonnet", "haiku", "opus"):
        o, _, _ = total(rs, {}, 300, fam)
        print(f"Model alone, all on {fam}: ${sum(o.values()):.2f} (" + ", ".join(f"{ro} {o[ro]:.2f}" for ro in ORCH) + ")")
