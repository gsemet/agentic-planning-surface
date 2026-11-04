"""Fresh-coder reference: cold start and re-exploration before the first source edit, by round; ctx at first edit."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
SRC = re.compile(r"/(src|test|tests|scripts|media|e2e)/|\.(ts|tsx|js|mjs|css|py)\b")
def src_edit(tr):
    if tr["name"] in ("Edit", "Write", "NotebookEdit"): return bool(SRC.search(tr.get("path", ""))) and not re.search(r"/(reports|reviews)/|\.md$", tr.get("path", ""))
    if tr["name"] == "Bash": c = tr.get("cmd", ""); return bash_kind(c) == "write-shell" and bool(SRC.search(c)) and not re.search(r"reports/|reviews/", c)
    return False
def rnd(d):
    m = re.search(r"round[- ]?(\d)|\br(\d)\b", d.lower()); return int(next(g for g in m.groups() if g)) if m else None
out = {}
print("| Round | Coders | First-turn cost p50 | Turns to first src edit p50 | $ before first edit p50 / mean | ctx at first edit p50 / mean | handover-note candidates |")
print("| --- | --- | --- | --- | --- | --- | --- |")
G = collections.defaultdict(list)
for w in W:
    if w["wrole"] != "coder": continue
    k = rnd(w["desc"])
    if k is None: continue
    T = w["turns"]; j = next((i for i, t in enumerate(T) if any(src_edit(tr) for tr in t["tools"])), None)
    if j is None: continue
    G[min(k, 3)].append((T[0]["cost"], j, sum(t["cost"] for t in T[:j]), ctx(T[j]), w["fact"], T[0]["fam"]))
for k in sorted(G):
    v = G[k]
    print(f"| {k}{'+' if k==3 else ''} | {len(v)} | ${st.median([x[0] for x in v]):.3f} | {st.median([x[1] for x in v]):.0f} | ${st.median([x[2] for x in v]):.2f} / ${st.mean([x[2] for x in v]):.2f} | {st.median([x[3] for x in v])/1e3:.0f}k / {st.mean([x[3] for x in v])/1e3:.0f}k | |")
    out[k] = dict(cost_pre_med=st.median([x[2] for x in v]), cost_pre_mean=st.mean([x[2] for x in v]), ctx_med=st.median([x[3] for x in v]), ctx_mean=st.mean([x[3] for x in v]), n=len(v))
json.dump(out, open(os.path.join(HERE, "..", "..", "data", "A2", "fresh_ref.json"), "w"))
# by model for round 2+
for fam in ("sonnet", "opus"):
    v = [x for k in (2, 3) for x in G[k] if x[5] == fam]
    if v: print(f"round 2+ {fam}: n={len(v)} $ before first edit p50 ${st.median([x[2] for x in v]):.2f} mean ${st.mean([x[2] for x in v]):.2f}")
