"""Item 4: small-context sub-levers, each alone on top of L2+L3, 5-min and 1-h TTL."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_sim import *
rows, byid = load_all(); calibrate(rows)
OR = [r for r in rows if r["role"] in ORCH]
def tot(lv, ttl=300, cap=None, mode="rotate", role=None):
    return sum(simulate(r, lv, ttl, None, cap, mode)[0] for r in OR if role is None or r["role"] == role)
for nm, base in (("low", {"waits": "low", "mech": "low"}), ("high", {"waits": "high", "mech": "high"})):
    print(f"\n## On top of L2+L3 {nm}")
    print("| Sub-lever | Foreman 5-min | Driver (all variants) 5-min | Total 5-min | Total 1-h |"); print("|---|---|---|---|---|")
    b5 = tot(base); b1 = tot(base, 3600); bf = tot(base, role="orchestrator")
    print(f"| (L2+L3 only) | {bf:.2f} | {b5-bf:.2f} | {b5:.2f} | {b1:.2f} |")
    for label, extra, cap, mode in (("(a) hand-back cap 300 tok", {"handback": 300}, None, "rotate"),
                                    ("(a) hand-back cap 600 tok", {"handback": 600}, None, "rotate"),
                                    ("(b) crf status 400 tok instead of status reads", {"status": 400}, None, "rotate"),
                                    ("(c) rotation at 60k", {}, 60e3, "rotate"), ("(c) rotation at 100k", {}, 100e3, "rotate"), ("(c) rotation at 150k", {}, 150e3, "rotate"),
                                    ("(d) auto-compaction at 60k", {}, 60e3, "compact"), ("(d) auto-compaction at 100k", {}, 100e3, "compact"), ("(d) auto-compaction at 150k", {}, 150e3, "compact")):
        lv = dict(base, **extra); f = tot(lv, 300, cap, mode, "orchestrator"); a = tot(lv, 300, cap, mode); a1 = tot(lv, 3600, cap, mode)
        print(f"| {label} | {f:.2f} ({f-bf:+.2f}) | {a-f:.2f} ({(a-f)-(b5-bf):+.2f}) | {a:.2f} ({a-b5:+.2f}) | {a1:.2f} ({a1-b1:+.2f}) |")
