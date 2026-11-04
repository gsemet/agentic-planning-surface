"""2. Long suites and waits: rebuild events in workers, outcomes, and options (a)-(d)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
src = open(os.path.join(HERE, "d_lever2.py")).read()
exec(src[src.index("def excess"):src.index("reb = collections")])
mis = 0
EV = []
for w in W:
    r = byid[w["meta"]["agent_id"]]
    if len(r["turns"]) != len(w["turns"]): mis += 1; continue
    T = r["turns"]
    for i, t in enumerate(T):
        if not rebuild(t, i): continue
        wf = waited_for(r, i); g = gap(T, i)
        fl = set(); 
        for x in t["inputs"]:
            if x[0] == "tool_result": fl |= set(x[2][5]); 
        edits_after = any(any(tool_kind(y) in ("edit-src", "edit-other", "bash:write-shell") for y in u["tools"]) for u in T[i:])
        tail = sum(u["cost"] for u in T[i:]); tail_turns = len(T) - i
        EV.append(dict(aid=w["meta"]["agent_id"], wr=w["wrole"], fact=w["fact"], i=i, gap=g, wf=wf, ex=excess(t), wcost=write_price(t), ctx=ctx(t), fam=t["fam"],
                       fail="fail" in fl, edits_after=edits_after, tail=tail, tail_turns=tail_turns, n=len(T)))
print("agents with turn mismatch:", mis)
json.dump(EV, open(os.path.join(HERE, "..", "..", "data", "A2", "rebuild_events.json"), "w"))
def grp(wf):
    if wf.startswith("Bash: long suite"): return "long suite (fg)"
    if wf.startswith("Bash: CI watch"): return "CI watch/poll (fg)"
    if wf == "background task notification": return "bg task notification"
    if wf.startswith("wait tool"): return "wait tool (Monitor/TaskOutput)"
    if wf.startswith("resumed after its own hand-back"): return "kept alive after hand-back"
    if wf.startswith("Bash: fast"): return "fast gates"
    if wf in ("message from main/user", "peer message"): return "steering/peer"
    if "ui-drive" in wf: return "UI drive (real window)"
    return "other"
print("\n| Role | Waited for | Rebuilds | Excess $ | gap 5-10 min | gap 10-15 | gap 15-60 | >1h | fail flag | edits after | median ctx | tail $ after (mean) |")
print("|" + " --- |" * 12)
agg = collections.defaultdict(list)
for e in EV: agg[(e["wr"], grp(e["wf"]))].append(e)
for (wr, k), v in sorted(agg.items(), key=lambda x: (WROLES.index(x[0][0]), -sum(e["ex"] for e in x[1]))):
    b = lambda lo, hi: sum(1 for e in v if lo <= e["gap"] < hi)
    print(f"| {wr} | {k} | {len(v)} | ${sum(e['ex'] for e in v):.2f} | {b(300,600)} | {b(600,900)} | {b(900,3600)} | {b(3600,1e9)} | {sum(e['fail'] for e in v)} | {sum(e['edits_after'] for e in v)} | {st.median([e['ctx'] for e in v])/1e3:.0f}k | ${st.mean([e['tail'] for e in v]):.2f} |")
