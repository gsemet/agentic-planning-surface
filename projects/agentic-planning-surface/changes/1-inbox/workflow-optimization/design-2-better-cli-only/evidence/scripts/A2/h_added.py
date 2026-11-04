"""Added costs of the sketch: mechanical commands per CR (runner agents), small-agent cost, extra rounds."""
import sys, os, statistics as st; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
rows, byid = load()
FACT = lambda r: r["run"] is not None or r["ws"] == "CR pipeline before run 1"
def cr_for(r):
    for d in [r["desc"]] + [byid[a]["desc"] for a in r["ancestors"] if a in byid]:
        c = cr_of(d)
        if c: return c
    return None
# 1. driver mechanical commands per CR (runs 1-5)
per = collections.defaultdict(collections.Counter)
for r in rows:
    if r["run"] and r["role"] in ("driver", "task driver", "integrator"):
        key = (r["run"], cr_for(r) or "?", r["desc"] if r["role"] != "driver" else "")
        for t in r["turns"]:
            for x in t["tools"]:
                k = tool_kind(x)
                per[(r["run"], cr_for(r) or "?")][k] += 1
                per[(r["run"], cr_for(r) or "?")]["ALL"] += 1
                if k.startswith("bash:"): per[(r["run"], cr_for(r) or "?")]["BASH"] += 1
vals = [v for k, v in per.items() if k[1] != "135"]
print("Drivers in runs 1-5 (excl. CR 135): CRs", len(vals), "median tool calls/CR", st.median([v["ALL"] for v in vals]), "median Bash/CR", st.median([v["BASH"] for v in vals]))
agg = collections.Counter()
for v in vals: agg.update(v)
print("  tool kinds per CR (mean):", {k: round(n / len(vals), 1) for k, n in agg.most_common(16)})
v135 = per.get(("run4/5", "135"), collections.Counter())
print("  CR 135 task drivers + integrators: tool calls", v135["ALL"], "bash", v135["BASH"])
# 2. rounds per CR in factory scope
rounds = collections.defaultdict(int)
for r in rows:
    if FACT(r) and r["role"] == "coder/writer":
        c = cr_for(r)
        m = re.search(r"round[- ]?(\d)|\br(\d)\b", r["desc"].lower())
        k = int(next(g for g in m.groups() if g)) if m else 1
        if c: rounds[c] = max(rounds[c], k)
rv = list(rounds.values())
print(f"\nRounds per CR (factory scope, from coder descriptions): CRs {len(rv)}, mean {st.mean(rv):.2f}, median {st.median(rv)}, share >1: {sum(1 for x in rv if x>1)/len(rv):.0%}, share >=3: {sum(1 for x in rv if x>=3)/len(rv):.0%}")
# 3. small-agent cost: real small agents (<=3 turns) and haiku
small = [r for r in rows if not r["meta"].get("main") and len(r["turns"]) <= 3]
for fam in ("haiku", "sonnet", "opus"):
    s = [r for r in small if r["turns"][0]["fam"] == fam]
    if s: print(f"agents with <=3 turns on {fam}: n={len(s)}, median cost ${st.median([r['cost'] for r in s]):.4f}, median first ctx {st.median([ctx(r['turns'][0]) for r in s])/1e3:.0f}k")
hk = [r for r in rows if r["turns"] and r["turns"][0]["fam"] == "haiku"]
print("haiku agents:", [(r["desc"][:30], len(r["turns"]), round(r["cost"], 4), round(ctx(r["turns"][0]) / 1e3)) for r in hk][:10])
# 4. extra rounds: long-suite failures inside coders that the coder then fixed (would become a new round)
fails = 0; crs_f = set(); coders = 0
for r in rows:
    if not (FACT(r) and r["role"] == "coder/writer"): continue
    coders += 1
    T = r["turns"]
    for i, t in enumerate(T):
        for x in t["inputs"]:
            if x[0] != "tool_result" or x[2][0] != "Bash": continue
            k = bash_kind(x[2][1])
            long_ = k in ("gate-long", "poll") or (i > 0 and gap(T, i) and gap(T, i) > 300)
            if long_ and (x[2][2] or "fail" in x[2][5]):
                later = any(any(tool_kind(y) in ("edit-src", "edit-other", "bash:write-shell") for y in u["tools"]) for u in T[i:])
                if later: fails += 1; crs_f.add(cr_for(r))
print(f"\nFactory coders: {coders}; long-suite/CI failures followed by more edits in the same coder: {fails} (CRs {len(crs_f)})")
r2 = [r for r in rows if r["role"] == "coder/writer" and re.search(r"round [2-9]|\br[2-9]\b", r["desc"].lower())]
print(f"round>=2 coders: n={len(r2)}, mean cost ${st.mean([r['cost'] for r in r2]):.2f}, median ${st.median([r['cost'] for r in r2]):.2f}")
