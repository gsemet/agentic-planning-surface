"""3c. Resume vs fresh: kept-alive agents (resumed after their own hand-back, rebuild) vs a fresh agent with a
hand-over note, simulated on the same agent's own turns. Plus the hand-over note on round-2+ coders."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
D = os.path.join(HERE, "..", "..", "data", "A2")
EV = json.load(open(os.path.join(D, "rebuild_events.json"))); FR = json.load(open(os.path.join(D, "fresh_ref.json")))
WB = {w["meta"]["agent_id"]: w for w in W}
def first_work(T):
    for j, t in enumerate(T):
        if any(tr["name"] in ("Edit", "Write") or (tr["name"] == "Bash" and bash_kind(tr.get("cmd", "")) == "write-shell") for tr in t["tools"]): return j
    return min(len(T) - 1, 5)
R = collections.defaultdict(collections.Counter)
# all hand-back resumes, not only rebuilds: every turn triggered right after an own SubagentHandback
for w in W:
    T = w["turns"]; hb = [i for i, t in enumerate(T) if any(tr["name"] == "SubagentHandback" for tr in t["tools"])]
    for h in hb:
        i = h + 1
        if i >= len(T): continue
        g = gap(T, i); r = R[w["wrole"]]
        nxt = [x for x in hb if x > h]; end = nxt[0] + 1 if nxt else len(T)
        seg = T[i:end]; seg_cost = sum(t["cost"] for t in seg)
        j = first_work(T); explore = sum(t["cost"] for t in T[:j]); cfirst = ctx(T[j])
        delta = max(0, ctx(T[i]) - cfirst)
        fresh_tail = sum(max(0.0, t["cost"] - min(delta, t["cr"]) * PRICE[t["fam"]][3] / 1e6) for t in seg[1:])
        r["n"] += 1; r["warm"] += g < 300; r["seg"] += seg_cost
        for lab, f in (("note", 0.5), ("nonote", 1.0)):
            r["fresh_" + lab] += f * explore + fresh_tail
        r["ctx"] += ctx(T[i])
        if g >= 300:
            r["c_n"] += 1; r["c_seg"] += seg_cost; r["c_fresh"] += 0.5 * explore + fresh_tail; r["c_fresh_nn"] += explore + fresh_tail
print("| Role | Resumes after own hand-back | of which within 5 min (warm) | Cost of resumed segments | Fresh agent + note (50 % re-exploration) | Fresh, no note | Saving with note |")
print("| --- | --- | --- | --- | --- | --- | --- |")
for wr in WROLES:
    r = R[wr]
    if not r["n"]: continue
    print(f"| {wr} | {r['n']} | {r['warm']} | ${r['seg']:.2f} | ${r['fresh_note']:.2f} | ${r['fresh_nonote']:.2f} | ${r['seg']-r['fresh_note']:.2f} |")
print("\nCold resumes only (gap >= 5 min): rule 'resume if warm, fresh + note if cold'")
print("| Role | Cold resumes | Cost of resumed segments | Fresh + note | Fresh, no note | Saving with note | Saving without note |")
print("| --- | --- | --- | --- | --- | --- | --- |")
for wr in WROLES:
    r = R[wr]
    if r["c_n"]: print(f"| {wr} | {r['c_n']} | ${r['c_seg']:.2f} | ${r['c_fresh']:.2f} | ${r['c_fresh_nn']:.2f} | ${r['c_seg']-r['c_fresh']:.2f} | ${r['c_seg']-r['c_fresh_nn']:.2f} |")
# hand-over note on round-2+ coders (fresh by construction)
n2, n3 = FR["2"]["n"], FR["3"]["n"]
base = n2 * FR["2"]["cost_pre_mean"] + n3 * FR["3"]["cost_pre_mean"]
print(f"\nRound-2+ coders: {n2+n3}; re-exploration before first edit ${base:.2f} in the window; note cutting it 25-50 % saves ${0.25*base:.2f}-${0.5*base:.2f}")
