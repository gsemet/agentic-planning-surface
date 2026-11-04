import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
rows, byid = load()
HERE = os.path.dirname(os.path.abspath(__file__))
prs = json.load(open(os.path.join(HERE, "..", "data", "prs.json")))
lines = {}
for p in prs:
    m = re.match(r"change-requests/(\d{3})", p["headRefName"])
    if m and p["state"] == "MERGED": lines[m.group(1)] = lines.get(m.group(1), 0) + p["additions"] + p["deletions"]
ORCH = {"orchestrator", "driver", "stack driver", "task driver", "integrator"}
def cr_for(r):
    for d in [r["desc"]] + [byid[a]["desc"] for a in r["ancestors"] if a in byid]:
        c = cr_of(d)
        if c: return c
    return None
# split run3 orchestrator a21e1 by first CR 135 spawn
o3 = byid["a21e1ec0a8fc37d31"]
cut = next(t["ts"] for t in o3["turns"] if any(x[0] == "Agent" and "135" in x[1] for x in t["tools"]))
print("run3 orchestrator split at", cut)
def items():
    for r in rows:
        if not r["run"]: continue
        if r["meta"]["agent_id"] == "a21e1ec0a8fc37d31":
            a = sum(t["cost"] for t in r["turns"] if t["ts"] < cut); b = r["cost"] - a
            yield r, "run3", a; yield r, "run4/5", b
        else:
            yield r, r["run"], r["cost"]
runs = collections.defaultdict(lambda: {"cost": 0, "orch": 0, "roles": collections.Counter(), "crs": collections.Counter(), "shared": 0, "agents": 0, "t0": "9", "t1": "0"})
for r, run, c in items():
    R = runs[run]; R["cost"] += c; R["roles"][r["role"]] += c; R["agents"] += 1
    if r["turns"]:
        R["t0"] = min(R["t0"], r["turns"][0]["ts"]); R["t1"] = max(R["t1"], r["turns"][-1]["ts"])
    if r["role"] in ORCH: R["orch"] += c
    cr = cr_for(r)
    if r["role"] in ("orchestrator", "stack driver") or cr is None: R["shared"] += c
    else: R["crs"][cr] += c
print("\n| Run | CRs | Agents | Window (UTC) | Subtree cost | Orchestration own cost (orch+drivers+stack+task drivers+integrator) | Overhead | Cost per CR (all-in) | Coder+reviewer per CR |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for run in ["run1", "run2", "run3", "run4/5"]:
    R = runs[run]; n = len(R["crs"])
    cw = R["roles"]["coder/writer"] + R["roles"]["reviewer"]
    print(f"| {run} | {n} | {R['agents']} | {R['t0'][5:16]} → {R['t1'][5:16]} | ${R['cost']:.2f} | ${R['orch']:.2f} | {100*R['orch']/R['cost']:.0f}% | ${R['cost']/n:.2f} | ${cw/n:.2f} |")
    print("   roles:", {k: round(v, 2) for k, v in R["roles"].most_common()}, "shared:", round(R["shared"], 2))
print("\nPer CR (own subtree excl. orchestrator + stack driver; lines = merged PR additions+deletions):")
for run in ["run1", "run2", "run3", "run4/5"]:
    R = runs[run]
    s = []
    for cr, c in sorted(R["crs"].items()):
        l = lines.get(cr)
        s.append(f"{cr}: ${c:.2f}" + (f" / {l} lines (${100*c/l:.2f}/100)" if l else ""))
    print(f"- {run}: " + "; ".join(s))
# detail per CR: roles and rounds
print("\nPer CR role split & rounds:")
for run in ["run1", "run2", "run3", "run4/5"]:
    for cr in sorted(runs[run]["crs"]):
        rc = collections.Counter(); rounds = 0; nag = 0
        for r in rows:
            if r["run"] == run and cr_for(r) == cr and r["role"] not in ("orchestrator", "stack driver"):
                rc[r["role"]] += r["cost"]; nag += 1
                m = re.search(r"round (\d)|\br(\d)\b", r["desc"].lower())
                if m and r["role"] == "coder/writer": rounds = max(rounds, int(m.group(1) or m.group(2)))
        print(f"  {run} CR {cr}: agents {nag} rounds(max coder) {rounds} ", {k: round(v, 2) for k, v in rc.most_common()})
# pre-run-1 orchestrated pipeline per top orchestrator
print("\nCR pipeline before run 1, by top-level agent (orchestration own vs subtree):")
tops = collections.defaultdict(lambda: [0, 0, 0, set()])
for r in rows:
    if r["ws"] != "CR pipeline before run 1": continue
    k = r["top"]["meta"]["agent_id"]
    tops[k][0] += r["cost"]
    if r["role"] in ORCH: tops[k][1] += r["cost"]
    tops[k][2] += 1
    c = cr_for(r)
    if c: tops[k][3].add(c)
for k, v in sorted(tops.items(), key=lambda x: -x[1][0])[:25]:
    print(f"  {byid[k]['desc'][:50]:50s} {k} subtree ${v[0]:.2f} orch ${v[1]:.2f} ({100*v[1]/max(v[0],1e-9):.0f}%) agents {v[2]} CRs {len(v[3])}")
tot = sum(v[0] for v in tops.values()); orc = sum(v[1] for v in tops.values())
print(f"  TOTAL pre-run1 ${tot:.1f} orch ${orc:.1f} ({100*orc/tot:.0f}%)")
json.dump({k: {"cost": v["cost"], "orch": v["orch"], "crs": dict(v["crs"])} for k, v in runs.items()}, open(os.path.join(HERE, "..", "data", "runs.json"), "w"))
