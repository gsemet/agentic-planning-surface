"""1c. Simulated payload cuts on real turns: harness prefix (tool schemas, skill listing, wrong AGENTS.md)
and role-card cuts (brief + instruction files read by tool) at -30 % / -50 %."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
RULES = re.compile(r"(AGENTS|CLAUDE|CONTRIBUTING|README)\.md|constitution|\.agents/guidelines/|\.agents/glossary|guideline|skills/[^ ]*(SKILL\.md|references/)")
def tgt(tr):
    if tr["name"] == "Read": return tr.get("path", "")
    if tr["name"] == "Bash":
        c = strip_cmd(tr.get("cmd", ""))
        if re.match(r"^(cat|head|tail|sed -n|nl|awk)", c): return c[:400]
    return None
res = collections.defaultdict(collections.Counter)
for w in W:
    s = w["start"]; wr = w["wrole"]
    art = s["toolsizes"].get("Artifact", 0) / CPT
    extra_tools = sum(s["toolsizes"].get(k, 0) for k in ("Agent", "ListAgents", "ReportFindings")) / CPT
    sk = s["att"].get("skill_listing", 0) / CPT
    wp = sum(n for p, ty, n in s["instr"] if "agentic-coding-white-paper/AGENTS.md" in p or "MEMORY.md" in p) / CPT
    res[wr]["artifact"] += cut_saving(w, [(0, 0, art)])
    res[wr]["agent/list/report tools"] += cut_saving(w, [(0, 0, extra_tools)])
    res[wr]["skill listing"] += cut_saving(w, [(0, 0, sk)])
    res[wr]["wrong AGENTS.md+MEMORY"] += cut_saving(w, [(0, 0, wp)])
    res[wr]["ALL prefix"] += cut_saving(w, [(0, 0, art + extra_tools + sk + wp)])
    # role card = brief (prefix end) + rule/skill files read by tool, at their real positions
    pos0 = ctx(w["turns"][0]) - s["brief"] / CPT
    rp = result_pos(w)
    card = [(0, pos0, s["brief"] / CPT)]
    for t in w["turns"]:
        for tr in t["tools"]:
            g = tgt(tr)
            if g and RULES.search(g) and tr.get("rc") and tr["id"] in rp:
                j, pos = rp[tr["id"]]; card.append((j, pos, tr["rc"] / CPT))
    tok = sum(c[2] for c in card)
    res[wr]["card tokens"] += tok; res[wr]["n"] += 1
    for f in (0.3, 0.5):
        res[wr][f"card -{int(f*100)}%"] += cut_saving(w, [(a, b, c * f) for a, b, c in card])
    res[wr]["cost"] += w["cost"]; res[wr]["turns"] += len(w["turns"])
print("| Role | Agents | Turns | Cost | Role card tokens/agent (brief + rules read) | Card -30 % | Card -50 % | Drop Artifact tool (15.5k) | Drop Agent/ListAgents/ReportFindings | Drop skill listing (5.1k) | Drop wrong AGENTS.md + MEMORY (3.2k) | All prefix cuts | All prefix, % of role cost |")
print("|" + " --- |" * 13)
tot = collections.Counter()
for wr in WROLES:
    r = res[wr]
    for k in r: tot[k] += r[k]
    print(f"| {wr} | {r['n']} | {r['turns']} | ${r['cost']:.1f} | {r['card tokens']/r['n']/1e3:.1f}k | ${r['card -30%']:.2f} | ${r['card -50%']:.2f} | ${r['artifact']:.2f} | ${r['agent/list/report tools']:.2f} | ${r['skill listing']:.2f} | ${r['wrong AGENTS.md+MEMORY']:.2f} | ${r['ALL prefix']:.2f} | {100*r['ALL prefix']/r['cost']:.1f}% |")
r = tot
print(f"| all workers | {r['n']} | {r['turns']} | ${r['cost']:.1f} | {r['card tokens']/r['n']/1e3:.1f}k | ${r['card -30%']:.2f} | ${r['card -50%']:.2f} | ${r['artifact']:.2f} | ${r['agent/list/report tools']:.2f} | ${r['skill listing']:.2f} | ${r['wrong AGENTS.md+MEMORY']:.2f} | ${r['ALL prefix']:.2f} | {100*r['ALL prefix']/r['cost']:.1f}% |")
print("\nper week = window x 0.92")
