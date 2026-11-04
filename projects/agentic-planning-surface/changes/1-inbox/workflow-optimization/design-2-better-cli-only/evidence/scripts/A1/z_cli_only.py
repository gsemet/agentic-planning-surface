"""Design 2, CLI only: original tree (orchestrator = subagent, 5-min TTL, no /loop, no compaction cap).
Levers: crf wait (L2), crf collapses (L3), hand-back schema + crf status (L4ab).
Drivers may re-arm a crf wait under the TTL, but only when their last action was that wait
(never while blocked on a foreground child). The orchestrator never re-arms."""
import sys, os, inspect; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a1_sim
from a1_sim import *
src = inspect.getsource(a1_sim.simulate)
src = src.replace("out_rate = None; ticks_n = [0]", "out_rate = None; ticks_n = [0]; prev_tag = ''")
src = src.replace("elif tick and g is not None", "elif tick and prev_tag == 'wait-launch' and g is not None")
src = src.replace("S_prev = S; last_end = ts(t[\"ts_last\"])", "S_prev = S; last_end = ts(t[\"ts_last\"]); prev_tag = tag[i]")
assert src.count("prev_tag") == 3
exec(src, a1_sim.__dict__); sim = a1_sim.simulate
rows, byid = load_all(); calibrate(rows)
WEEK = 7 / 7.61
LOW = {"waits": "low", "mech": "low", "handback": 600, "status": 800}
HIGH = {"waits": "high", "mech": "high", "handback": 300, "status": 400}
SC = [("baseline", {}, False), ("cli low", LOW, False), ("cli high", HIGH, False),
      ("cli low + driver re-arm", LOW, True), ("cli high + driver re-arm", HIGH, True)]
print("| Scenario | " + " | ".join(D2NAME[ro] for ro in ORCH) + " | Total window | Total /wk |")
res = {}
for name, lv, tick in SC:
    vals = []
    for ro in ORCH:
        tk = tick and ro != "orchestrator"
        vals.append(sum(sim(r, lv, 300, None, None, "rotate", tk)[0] for r in rows if r["role"] == ro))
    res[name] = vals
    print(f"| {name} | " + " | ".join(f"{v:.2f}" for v in vals) + f" | {sum(vals):.2f} | {sum(vals)*WEEK:.1f} |")
b = res["baseline"]
print("\nSaving per week vs simulated baseline")
for name in res:
    print(name, [round((x - y) * WEEK, 1) for x, y in zip(b, res[name])], round((sum(b) - sum(res[name])) * WEEK, 1))
