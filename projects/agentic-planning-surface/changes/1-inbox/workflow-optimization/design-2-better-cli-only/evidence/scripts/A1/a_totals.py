import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
rows, byid = load()
cat = collections.Counter(); fam = collections.Counter(); turns = 0
for r in rows:
    for t in r["turns"]:
        p = PRICE[t["fam"]]; turns += 1
        cat["cache read"] += t["cr"] * p[3] / 1e6; cat["5-min write"] += t["w5"] * p[1] / 1e6
        cat["1-h write"] += t["w1h"] * p[2] / 1e6; cat["uncached input"] += t["in"] * p[0] / 1e6
        cat["output"] += t["out"] * p[4] / 1e6; fam[t["fam"]] += t["cost"]
T = sum(cat.values())
print(f"TOTAL ${T:.1f} agents {len(rows)} subagents {sum(1 for r in rows if not r['meta'].get('main'))} turns {turns}")
first = min(t["ts"] for r in rows for t in r["turns"]); last = max(t["ts"] for r in rows for t in r["turns"])
print("first/last turn (UTC):", first, last)
print("\n| Category | Cost | Share |"); print("| --- | --- | --- |")
for k, v in cat.most_common(): print(f"| {k} | ${v:.1f} | {100*v/T:.1f}% |")
print("\nmodel:", {k: round(v, 1) for k, v in fam.items()})
print("\n| Role | Agents | Turns | Cost | Share | Cache read $ | 5m write $ | 1h write $ | Output $ |"); print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for role in ROLES:
    rs = [r for r in rows if r["role"] == role]
    if not rs: continue
    c = collections.Counter()
    for r in rs:
        for t in r["turns"]:
            p = PRICE[t["fam"]]; c["cr"] += t["cr"] * p[3] / 1e6; c["w5"] += t["w5"] * p[1] / 1e6; c["w1h"] += t["w1h"] * p[2] / 1e6; c["out"] += t["out"] * p[4] / 1e6; c["n"] += 1
    cost = sum(r["cost"] for r in rs)
    print(f"| {role} | {len(rs)} | {c['n']} | ${cost:.1f} | {100*cost/T:.1f}% | {c['cr']:.1f} | {c['w5']:.1f} | {c['w1h']:.1f} | {c['out']:.1f} |")
print("\n| Workstream | Agents | Cost | Share |"); print("| --- | --- | --- | --- |")
ws = collections.Counter(); wn = collections.Counter()
for r in rows:
    k = r["ws"] if not r["ws"].startswith("other:") else "misc (one-off tasks)"
    ws[k] += r["cost"]; wn[k] += 1
for k, v in ws.most_common(): print(f"| {k} | {wn[k]} | ${v:.1f} | {100*v/T:.1f}% |")
# per day
d = collections.Counter()
for r in rows:
    for t in r["turns"]: d[t["ts"][:10]] += t["cost"]
print("\nper day (UTC):", {k: round(v, 1) for k, v in sorted(d.items())})
# role x workstream for the factory-like streams
print("\nrole by workstream:")
for w in ["CR pipeline before run 1", "CR factory run1", "CR factory run2", "CR factory run3", "CR factory run4/5", "requirements base (CR 059/060)", "deep-UX fix plan", "CR 056 refactor"]:
    c = collections.Counter()
    for r in rows:
        if r["ws"] == w: c[r["role"]] += r["cost"]
    print(w, {k: round(v, 1) for k, v in c.most_common()})
