"""1. Anatomy per worker role."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
print("| Role | Agents | Turns | Cost | Cache read | 5m write | Output | Output share | Models (agents) | Turns/agent p50 | Ctx/turn p50 | p90 | First ctx p50 | Last ctx p50 | Out tok/turn mean | p50 | p90 |")
print("|" + " --- |" * 17)
tot = collections.Counter()
for wr in WROLES:
    ws = [w for w in W if w["wrole"] == wr]
    if not ws: continue
    c = collections.Counter(); outs = []; ctxs = []; fam = collections.Counter()
    for w in ws:
        fam[w["turns"][0]["fam"]] += 1
        for t in w["turns"]:
            p = PRICE[t["fam"]]
            c["cr"] += t["cr"] * p[3] / 1e6; c["w"] += (t["w5"] * p[1] + t["w1h"] * p[2]) / 1e6; c["o"] += t["out"] * p[4] / 1e6; c["n"] += 1
            outs.append(t["out"]); ctxs.append(ctx(t))
    cost = sum(w["cost"] for w in ws); tot["cost"] += cost
    print(f"| {wr} | {len(ws)} | {c['n']} | ${cost:.1f} | ${c['cr']:.1f} | ${c['w']:.1f} | ${c['o']:.1f} | {100*c['o']/cost:.0f}% | {dict(fam)} | {st.median([len(w['turns']) for w in ws]):.0f} | {st.median(ctxs)/1e3:.0f}k | {pct(ctxs,.9)/1e3:.0f}k | {st.median([ctx(w['turns'][0]) for w in ws])/1e3:.0f}k | {st.median([ctx(w['turns'][-1]) for w in ws])/1e3:.0f}k | {sum(outs)/len(outs):.0f} | {st.median(outs):.0f} | {pct(outs,.9):.0f} |")
print("total worker cost", round(tot["cost"], 1))
# factory-scope split
print("\nFactory scope (runs 1-5 + pre-run-1 CR batches) per role:")
for wr in WROLES:
    ws = [w for w in W if w["wrole"] == wr and w["fact"]]
    if ws: print(f"  {wr}: agents {len(ws)} turns {sum(len(w['turns']) for w in ws)} cost ${sum(w['cost'] for w in ws):.1f}")
# Model x role
print("\nCost by model family per role:")
for wr in WROLES:
    c = collections.Counter()
    for w in W:
        if w["wrole"] == wr:
            for t in w["turns"]: c[t["fam"]] += t["cost"]
    print(f"  {wr}: " + ", ".join(f"{k} ${v:.1f}" for k, v in c.most_common()))
# Output: visible text vs tool input vs (implied) thinking
print("\nOutput tokens composition (chars/3.5 for visible text and tool inputs; remainder ~ thinking):")
for wr in WROLES:
    o = vis = 0; thinkturns = 0; n = 0
    for w in W:
        if w["wrole"] != wr: continue
        for t in w["turns"]:
            o += t["out"]; vis += (t["text"] + t["tin"]) / 3.5; n += 1; thinkturns += t["think"] > 0
    print(f"  {wr}: output {o/1e6:.2f} MTok, visible text+tool input ~{vis/1e6:.2f} MTok ({100*vis/o:.0f}%), implied thinking ~{100*(1-vis/o):.0f}%, turns with a thinking block {100*thinkturns/n:.0f}%")
