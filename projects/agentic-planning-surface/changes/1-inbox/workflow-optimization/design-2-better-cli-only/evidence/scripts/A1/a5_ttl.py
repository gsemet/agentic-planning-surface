"""Item 5: TTL per role after levers 2-4, from real gap distributions; keep-warm ticks as an alternative."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_sim import *
rows, byid = load_all(); calibrate(rows)
LOW = {"waits": "low", "mech": "low", "handback": 600, "status": 800}
HIGH = {"waits": "high", "mech": "high", "handback": 300, "status": 400}
print("## Gaps between kept turns after levers 2-4 (high), share of turns")
print("| Role | kept turns | <5 min | 5-15 min | 15-60 min | >1 h | median gap of >5 min gaps (min) |"); print("|---|---|---|---|---|---|---|")
for ro in ORCH:
    rs = [r for r in rows if r["role"] == ro]; b = collections.Counter(); big = []
    for r in rs:
        keep, *_ = plan(r, HIGH); last = None
        for i, t in enumerate(r["turns"]):
            if not keep[i]: continue
            if last is not None:
                g = (ts(t["ts"]) - last).total_seconds()
                b["<5" if g < 300 else "5-15" if g < 900 else "15-60" if g < 3600 else ">1h"] += 1
                if g >= 300: big.append(g / 60)
            last = ts(t["ts_last"])
    n = sum(b.values())
    print(f"| {D2NAME[ro]} | {n} | {100*b['<5']/n:.0f}% | {100*b['5-15']/n:.0f}% | {100*b['15-60']/n:.0f}% | {100*b['>1h']/n:.1f}% | {st.median(big):.0f} |")
print("\n## Cost per role after levers 2-4 (+ rotation), by cache policy ($ window)")
for nm, lv, cap in (("low", LOW, 150e3), ("high", HIGH, 100e3)):
    print(f"\n### {nm} levers, rotation at {int(cap/1e3)}k")
    print("| Role | 5-min | 5-min + keep-warm ticks (every 4.5 min) | 1-h | 1-h + keep-warm ticks (every 59.5 min) | best |"); print("|---|---|---|---|---|---|")
    for ro in ORCH:
        rs = [r for r in rows if r["role"] == ro]
        v = [sum(simulate(r, lv, ttl, None, cap, "rotate", tick)[0] for r in rs) for ttl, tick in ((300, False), (300, True), (3600, False), (3600, True))]
        names = ["5-min", "5-min+ticks", "1-h", "1-h+ticks"]
        print(f"| {D2NAME[ro]} | " + " | ".join(f"{x:.2f}" for x in v) + f" | {names[v.index(min(v))]} |")
