"""5. Model and effort per role: same tokens repriced; thinking share; verdict data by model (quality guard)."""
import sys, os, glob; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
print("| Role | Today (mix) | Opus share of cost | All Sonnet | All Opus | All Haiku | Output $ | Est. thinking $ (output minus visible text/tool input) | Effort -30 % thinking | -50 % |")
print("|" + " --- |" * 10)
for wr in WROLES:
    ws = [w for w in W if w["wrole"] == wr]; c = collections.Counter()
    for w in ws:
        for t in w["turns"]:
            c["today"] += t["cost"]
            if t["fam"] == "opus": c["opus_share"] += t["cost"]
            for f in ("sonnet", "opus"): c[f] += tcost(t, f)
            c["haiku"] += tcost(t, "haiku") * (5 if ctx(t) > 100000 else 1)  # Haiku 5.5: x5 above 100K-token prompts
            c["haiku_turns_over100k"] += ctx(t) > 100000; c["turns"] += 1
            p = PRICE[t["fam"]]; c["out"] += t["out"] * p[4] / 1e6
            th = max(0, t["out"] - (t["text"] + t["tin"]) / 3.5); c["think"] += th * p[4] / 1e6
    print(f"| {wr} | ${c['today']:.1f} | {100*c['opus_share']/c['today']:.0f}% | ${c['sonnet']:.1f} | ${c['opus']:.1f} | ${c['haiku']:.2f} | ${c['out']:.1f} | ${c['think']:.1f} | ${0.3*c['think']:.1f} | ${0.5*c['think']:.1f} |  (turns >100k ctx: {100*c['haiku_turns_over100k']/c['turns']:.0f}%)")
# verdicts by inspector model (from hand-back text)
paths = {os.path.basename(p)[6:-6]: p for p in glob.glob(os.path.expanduser("~/.claude/projects/*/*/subagents/*.jsonl"))}
V = collections.Counter()
for w in W:
    if w["wrole"] != "inspector": continue
    txt = ""
    with open(paths[w["meta"]["agent_id"]], errors="replace") as f:
        for line in f:
            if "SubagentHandback" not in line: continue
            d = json.loads(line)
            for b in (d.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "SubagentHandback":
                    txt += (b.get("input") or {}).get("message", "")
    v = "FIX" if re.search(r"FIX-REQUIRED|FIX REQUIRED|REQUEST.CHANGES", txt) else "APPROVE" if re.search(r"APPROVE", txt) else "other"
    V[(w["turns"][0]["fam"], v)] += 1; V[(w["turns"][0]["fam"], "cost")] += w["cost"]; V[(w["turns"][0]["fam"], "n")] += 1
print("\nInspector verdicts by model (all inspectors):")
for f in ("sonnet", "opus"):
    n = V[(f, "n")]; print(f"  {f}: n={n} APPROVE {V[(f,'APPROVE')]} FIX-REQUIRED {V[(f,'FIX')]} ({100*V[(f,'FIX')]/n:.0f}%) other {V[(f,'other')]}, cost/agent ${V[(f,'cost')]/n:.3f}")
