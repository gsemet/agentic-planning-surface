"""Lever 1: orchestrators and drivers. Turn categories, tool kinds, rebuilds, steering turns."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
rows, byid = load()
ORCH = ["orchestrator", "driver", "stack driver", "task driver", "integrator"]
def scope(r):
    if r["run"]: return "runs 1-5"
    if r["ws"] == "CR pipeline before run 1": return "pre-run-1 CR batches"
    return "other workstreams"
def excess(t):  # rebuild write minus what a warm read would cost
    p = PRICE[t["fam"]]; return (t["w5"] * (p[1] - p[3]) + t["w1h"] * (p[2] - p[3])) / 1e6
def category(r, i):
    t = r["turns"][i]
    if i == 0: return "first turn (brief)"
    ks = [x[0] for x in t["inputs"]]
    if "steer" in ks: return "steer (message from main/user)"
    if "peer_msg" in ks: return "peer message"
    res = [x for x in t["inputs"] if x[0] == "tool_result"]
    exc = any(x[2][2] or set(x[2][5]) & {"conflict", "denied"} for x in res) or any("fail" in x[2][5] and bash_kind(x[2][1]) in ("gate-long", "gate-fast", "gh-ci", "poll") for x in res if x[2][0] == "Bash")
    hb = "handback" in ks; tn = "task_notif" in ks
    kinds = [tool_kind(x) for x in t["tools"]]
    if exc: return "exception (error/conflict/denied/failed gate or CI)"
    if hb and any(k == "spawn" for k in kinds): return "handback -> spawn next"
    if hb: return "handback handling"
    if tn: return "background wait resumed"
    if not kinds: return "text only / report"
    if any(k == "spawn" for k in kinds): return "spawn"
    if any(k == "sendmessage" for k in kinds): return "send message"
    if all(k.startswith("bash:") or k in ("read-status", "edit-status", "wait-tool", "read") for k in kinds):
        if any(k in ("edit-status",) or k == "bash:write-shell" for k in kinds): return "mechanical: status/table write"
        if any(k in ("bash:poll", "bash:sleep", "wait-tool", "bash:gh-ci") for k in kinds): return "mechanical: poll/wait/CI"
        if any(k.startswith("bash:git") or k.startswith("bash:gh") for k in kinds): return "mechanical: git/gh"
        if any(k.startswith("bash:gate") for k in kinds): return "mechanical: gates"
        return "mechanical: reads/other shell"
    return "other (edits src/other tools)"
agg = collections.defaultdict(lambda: collections.Counter())
tools = collections.defaultdict(collections.Counter)
steer_eps = collections.defaultdict(lambda: [0, 0, 0.0, 0.0])  # scope -> n msgs, turns, cost direct, cost episode
own = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    if r["role"] not in ORCH: continue
    sc = scope(r)
    o = own[(sc, r["role"])]; o["n"] += 1; o["cost"] += r["cost"]; o["turns"] += len(r["turns"])
    ep = None
    for i, t in enumerate(r["turns"]):
        c = category(r, i)
        a = agg[sc]; a[c + "|n"] += 1; a[c + "|$"] += t["cost"]
        if rebuild(t, i):
            o["rebuilds"] += 1; o["rebuild$"] += write_price(t); o["excess$"] += excess(t)
        for x in t["tools"]:
            tools[sc][tool_kind(x)] += 1
        ks = [x[0] for x in t["inputs"]]
        if i > 0 and "steer" in ks:
            se = steer_eps[sc]; se[0] += sum(1 for k in ks if k == "steer"); se[1] += 1; se[2] += t["cost"]; ep = True; se[3] += t["cost"]
        elif ep and trig(t) == "tool_result":
            steer_eps[sc][3] += t["cost"]; steer_eps[sc][1] += 0
        else:
            ep = None
print("| Scope | Role | Agents | Turns | Own cost | Rebuilds | Rebuild write $ | Rebuild excess vs warm read $ |")
print("| --- | --- | --- | --- | --- | --- | --- | --- |")
for (sc, ro), o in sorted(own.items()):
    print(f"| {sc} | {ro} | {o['n']} | {o['turns']} | ${o['cost']:.2f} | {o['rebuilds']} | ${o['rebuild$']:.2f} | ${o['excess$']:.2f} |")
for sc in agg:
    a = agg[sc]; T = sum(v for k, v in a.items() if k.endswith("|$")); N = sum(v for k, v in a.items() if k.endswith("|n"))
    print(f"\n### Turn categories, {sc}: {N} turns, ${T:.2f}")
    print("| Category | Turns | Cost | Share of cost |"); print("| --- | --- | --- | --- |")
    cats = sorted({k.split("|")[0] for k in a}, key=lambda c: -a[c + "|$"])
    for c in cats: print(f"| {c} | {a[c+'|n']} | ${a[c+'|$']:.2f} | {100*a[c+'|$']/T:.1f}% |")
    se = steer_eps[sc]
    print(f"steering: {se[0]} incoming messages from main/user, {se[1]} turns directly triggered, direct cost ${se[2]:.2f}, episode cost (incl. follow-up tool turns) ${se[3]:.2f}")
    tc = tools[sc]; TT = sum(tc.values())
    print(f"tool calls ({TT}):", ", ".join(f"{k} {v}" for k, v in tc.most_common(25)))
# per-agent top list for evidence
print("\nTop orchestration agents by own cost:")
for r in sorted([r for r in rows if r["role"] in ORCH], key=lambda r: -r["cost"])[:15]:
    ts_ = r["turns"]; avgctx = sum(ctx(t) for t in ts_) / len(ts_)
    rb = sum(1 for i, t in enumerate(ts_) if rebuild(t, i)); rbc = sum(write_price(t) for i, t in enumerate(ts_) if rebuild(t, i))
    st = sum(1 for i, t in enumerate(ts_) if i and "steer" in [x[0] for x in t["inputs"]])
    print(f"  {r['meta']['agent_id']} {r['desc'][:45]:45s} {scope(r):22s} ${r['cost']:.2f} turns {len(ts_)} avgctx {avgctx/1e3:.0f}k rebuilds {rb} (${rbc:.2f}) steer-turns {st} bash {sum(1 for t in ts_ for x in t['tools'] if x[0]=='Bash')}")
