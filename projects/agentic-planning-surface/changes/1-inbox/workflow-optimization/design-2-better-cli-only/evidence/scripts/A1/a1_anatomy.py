"""Item 1: anatomy per orchestration role (Foreman, Driver variants, main session)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_common import *
rows, byid = load_all()
# --- calibration of chars per token on orchestration agents
num = den = 0; ratios = []
for r in rows:
    if r["role"] not in ORCH: continue
    T = r["turns"]
    for i in range(1, len(T)):
        t, p = T[i], T[i - 1]
        if is_compact(t) or any(x[0] == "tool_result" and x[2][3] for x in t["inputs"]): continue
        ch = sum(x[1] for x in t["inputs"])
        d = ctx(t) - ctx(p) - p["out"]
        if ch > 2000 and d > 200: num += ch; den += d; ratios.append(ch / d)
print(f"(small-input pooled ratio {num/den:.2f} is biased by untracked per-turn reminders; CPT={CPT} from a1_calib.py is used)")

def band(g):
    if g is None: return "first"
    return "<5m" if g < 300 else "5-15m" if g < 900 else "15-60m" if g < 3600 else ">1h"

groups = collections.OrderedDict()
for ro in ORCH + ["main"]:
    groups[ro] = [r for r in rows if r["role"] == ro]
for sc in ["runs 1-5"]:
    for ro in ORCH: groups[ro + " @" + sc] = [r for r in rows if r["role"] == ro and scope(r) == sc]

print("\n## A. Anatomy per role (window)")
print("| Role | Agents | Turns | Turns/agent med (max) | Model $ | Cost | read | 5m w | 1h w | out | ctx med | p90 | max | 1st-turn ctx med | ctx growth/turn med | compactions | rebuilds (<5m/5-15/15-60/>1h) | rebuild write $ |")
print("|" + "---|" * 19)
for g, rs in groups.items():
    if not rs: continue
    T = [t for r in rs for t in r["turns"]]
    cs = [ctx(t) for t in T]
    fams = collections.Counter()
    comp = collections.Counter()
    for t in T:
        p = PRICE[t["fam"]]; fams[t["fam"]] += t["cost"]
        comp["r"] += t["cr"] * p[3] / 1e6; comp["w5"] += t["w5"] * p[1] / 1e6; comp["w1"] += t["w1h"] * p[2] / 1e6; comp["o"] += t["out"] * p[4] / 1e6
    first = [ctx(r["turns"][0]) for r in rs]
    grow = []
    for r in rs:
        if len(r["turns"]) > 3:
            grow.append((max(ctx(t) for t in r["turns"]) - ctx(r["turns"][0])) / len(r["turns"]))
    rb = collections.Counter(); rbw = 0
    for r in rs:
        for i, t in enumerate(r["turns"]):
            if rebuild(t, i):
                rb[band(gap(r["turns"], i))] += 1; rbw += write_price(t)
    n = [len(r["turns"]) for r in rs]
    print(f"| {D2NAME.get(g.split(' @')[0], g)}{' @'+g.split(' @')[1] if ' @' in g else ''} | {len(rs)} | {len(T)} | {st.median(n):.0f} ({max(n)}) | " + "/".join(f"{k} {v:.0f}" for k, v in fams.most_common()) +
          f" | ${sum(t['cost'] for t in T):.2f} | {comp['r']:.1f} | {comp['w5']:.1f} | {comp['w1']:.1f} | {comp['o']:.1f} | {st.median(cs)/1e3:.0f}k | {pct(cs,.9)/1e3:.0f}k | {max(cs)/1e3:.0f}k | {st.median(first)/1e3:.0f}k | {st.median(grow)/1e3 if grow else 0:.2f}k | {sum(r['compactions'] for r in rs)} | {rb['<5m']}/{rb['5-15m']}/{rb['15-60m']}/{rb['>1h']} | ${rbw:.2f} |")

print("\n## B. Context composition: what the agent carries (tokens = chars/CPT; carry cost = write once + read on each later turn until compaction/end)")
for g in ["orchestrator", "driver", "stack driver", "task driver", "main"]:
    rs = groups[g]
    agg = collections.defaultdict(lambda: [0, 0.0, 0, 0.0])  # n, tokens, turn-carries, $
    own_out = [0.0, 0.0]
    tot_read = 0.0
    for r in rs:
        T = r["turns"]
        # segment end index for each turn (next compaction)
        nxt = [len(T)] * len(T); last = len(T)
        for i in range(len(T) - 1, -1, -1):
            nxt[i] = last
            if is_compact(T[i]): last = i
        for i, t in enumerate(T):
            p = PRICE[t["fam"]]
            tot_read += t["cr"] * p[3] / 1e6
            if i == 0: continue
            carried = nxt[i] - i - 1
            for x in t["inputs"]:
                c = input_class(x); tok = in_tokens(x)
                a = agg[c]; a[0] += 1; a[1] += tok; a[2] += carried
                a[3] += tok * (p[1] + carried * p[3]) / 1e6 if t["fam"] != "opus" or not r["is_main"] else tok * (p[2] + carried * p[3]) / 1e6
            own_out[0] += t["out"]; own_out[1] += t["out"] * (nxt[i] - i - 1) * p[3] / 1e6
    print(f"\n### {D2NAME[g]} ({len(rs)} agents); total cache-read $ {tot_read:.2f}")
    print("| Input class | Items | Mean tokens | Mean turns carried | Carry cost $ |"); print("|---|---|---|---|---|")
    for c, a in sorted(agg.items(), key=lambda kv: -kv[1][3]):
        print(f"| {c} | {a[0]} | {a[1]/a[0]:.0f} | {a[2]/a[0]:.0f} | {a[3]:.2f} |")
    print(f"| (own output, read only) | – | – | – | {own_out[1]:.2f} |")

print("\n## C. Per-agent top 12 orchestration agents (evidence)")
print("| Agent | Role | Description | Scope | Model | Turns | Cost | ctx med/max | 1st ctx | compactions | rebuilds |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for r in sorted([r for r in rows if r["role"] in ORCH], key=lambda r: -r["cost"])[:12]:
    T = r["turns"]; cs = [ctx(t) for t in T]
    print(f"| `{r['meta']['agent_id']}` | {r['role']} | {r['desc'][:40]} | {scope(r)} | {collections.Counter(t['fam'] for t in T).most_common(1)[0][0]} | {len(T)} | ${r['cost']:.2f} | {st.median(cs)/1e3:.0f}k/{max(cs)/1e3:.0f}k | {cs[0]/1e3:.0f}k | {r['compactions']} | {sum(1 for i,t in enumerate(T) if rebuild(t,i))} |")
# first-turn brief size
print("\n## D. First prompt (brief) size, chars: median per role")
for g in ["orchestrator", "driver", "stack driver", "task driver"]:
    rs = groups[g]
    fp = [sum(x[1] for x in r["turns"][0]["inputs"]) for r in rs]
    print(g, f"median brief {st.median(fp):.0f} chars ≈ {st.median(fp)/CPT:.0f} tok; first-turn ctx median {st.median([ctx(r['turns'][0]) for r in rs])/1e3:.1f}k")
