"""2d. One-hour TTL per worker role, turn by turn; today and after waits are removed ((c)/(d))."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
D = os.path.join(HERE, "..", "..", "data", "A2")
EV = json.load(open(os.path.join(D, "rebuild_events.json")))
WAITS = {(e["aid"], e["i"]) for e in EV if e["wr"] in ("coder", "inspector") and (e["wf"].startswith("Bash: long") or e["wf"].startswith("Bash: CI") or e["wf"] == "background task notification")}
def turn_cost(T, i, ttl, warm=False):
    t = T[i]; p = PRICE[t["fam"]]; w = t["w5"] + t["w1h"]
    wp = p[1] if ttl == "5m" else p[2]
    if i > 0 and rebuild(t, i):
        g = gap(T, i)
        if warm or (ttl == "1h" and g < 3600):
            prev = ctx(T[i - 1]) + T[i - 1]["out"]; rd = min(prev, w)
            return (t["in"] * p[0] + (t["cr"] + rd) * p[3] + (w - rd) * wp + t["out"] * p[4]) / 1e6
    return (t["in"] * p[0] + t["cr"] * p[3] + w * wp + t["out"] * p[4]) / 1e6
print("| Role | Cost today (5 min) | 1-h TTL | Net 1-h | After waits removed: 5 min | After waits removed: 1-h | Net 1-h after |")
print("| --- | --- | --- | --- | --- | --- | --- |")
for wr in WROLES:
    c = collections.Counter()
    for w in W:
        if w["wrole"] != wr: continue
        T = w["turns"]; aid = w["meta"]["agent_id"]
        for i in range(len(T)):
            warm = (aid, i) in WAITS
            c["5m"] += turn_cost(T, i, "5m"); c["1h"] += turn_cost(T, i, "1h")
            c["5m_after"] += turn_cost(T, i, "5m", warm); c["1h_after"] += turn_cost(T, i, "1h", warm)
    print(f"| {wr} | ${c['5m']:.1f} | ${c['1h']:.1f} | {'+' if c['1h']>c['5m'] else ''}${c['1h']-c['5m']:.1f} | ${c['5m_after']:.1f} | ${c['1h_after']:.1f} | {'+' if c['1h_after']>c['5m_after'] else ''}${c['1h_after']-c['5m_after']:.1f} |")
