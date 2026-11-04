"""1b. First-turn context composition and the instruction payload (attached + read by tool)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
# chars per token calibration on first turns
ratios = []
for w in W:
    s = w["start"]; ch = s["sys"] + s["tools"] + sum(s["att"].values()) + s["brief"]
    t0 = w["turns"][0]
    if s["tools"] and ch: ratios.append(ctx(t0) / ch)
print(f"first-turn tokens per char: median {st.median(ratios):.3f} p10 {pct(ratios,.1):.3f} p90 {pct(ratios,.9):.3f} (n={len(ratios)}) -> chars/token {1/st.median(ratios):.2f}")
CPT = 1 / st.median(ratios)
print("\n| Role | n | First ctx p50 (tok) | System prompt | Tool schemas | Skill listing | Instruction files (CLAUDE/AGENTS/MEMORY) | Deferred tools + MCP | Other attachments | Brief p50 | Brief p90 |")
print("|" + " --- |" * 11)
for wr in WROLES:
    ws = [w for w in W if w["wrole"] == wr and w["start"]["tools"]]
    if not ws: continue
    f = lambda k: st.median([k(w["start"]) for w in ws]) / CPT
    print(f"| {wr} | {len(ws)} | {st.median([ctx(w['turns'][0]) for w in ws])/1e3:.1f}k | {f(lambda s: s['sys'])/1e3:.1f}k | {f(lambda s: s['tools'])/1e3:.1f}k | {f(lambda s: s['att'].get('skill_listing',0))/1e3:.1f}k | {f(lambda s: s['att'].get('instructions',0))/1e3:.1f}k | {f(lambda s: s['att'].get('deferred_tools_delta',0)+s['att'].get('mcp_instructions_delta',0))/1e3:.1f}k | {f(lambda s: sum(v for k,v in s['att'].items() if k not in ('skill_listing','instructions','deferred_tools_delta','mcp_instructions_delta')))/1e3:.1f}k | {f(lambda s: s['brief'])/1e3:.1f}k | {pct([w['start']['brief'] for w in ws],.9)/CPT/1e3:.1f}k |")
# which instruction files are attached
fc = collections.Counter(); fs = {}
for w in W:
    for p, ty, n in w["start"]["instr"]:
        fc[(w["wrole"], p.replace(os.path.expanduser("~"), "~"))] += 1; fs[p.replace(os.path.expanduser("~"), "~")] = n
print("\nAttached instruction files (agents, chars):")
for (wr, p), n in sorted(fc.items(), key=lambda x: (x[0][0], -x[1]))[:40]: print(f"  {wr:16s} {n:4d} {fs[p]:6d} {p}")
# tool schema sizes
ts_ = collections.Counter(); tn = collections.Counter()
for w in W:
    for k, v in w["start"]["toolsizes"].items(): ts_[k] += v; tn[k] += 1
print("\nTool schemas (mean chars when present, agents):")
for k, v in sorted(ts_.items(), key=lambda x: -x[1] / tn[x[0]]): print(f"  {k:28s} {v/tn[k]:7.0f} chars ~{v/tn[k]/CPT:6.0f} tok  in {tn[k]} agents")
# instruction reads by tool
CAT = [("project rules", re.compile(r"(AGENTS|CLAUDE|CONTRIBUTING|README)\.md|constitution|\.agents/guidelines/|\.agents/glossary|instructions\.md|guideline")),
       ("skill text", re.compile(r"skills/[^ ]*(SKILL\.md|references/)")),
       ("CR brief files", re.compile(r"(task|rules|00-request|STATE|RUN-BRIEF|ORCHESTRATOR)[^/ ]*\.md|/reports/|/reviews/|TASKS\.md|PRD"))]
def target(tr):
    if tr["name"] == "Read": return tr.get("path", "")
    if tr["name"] == "Bash":
        c = strip_cmd(tr.get("cmd", ""))
        if re.match(r"^(cat|head|tail|sed -n|nl|less|awk)", c): return c[:400]
    if tr["name"] == "Skill": return "skills/" + str(tr.get("skill")) + "/SKILL.md"
    return None
print("\nInstruction payload read by tool (whole agent life):")
print("| Role | Agents | Project rules: agents reading / mean tokens per reader | Skill text | CR brief files | Instruction tokens per agent mean (attached instr files + rules + skill) |")
print("| --- | --- | --- | --- | --- | --- |")
PAY = {}
for wr in WROLES:
    ws = [w for w in W if w["wrole"] == wr]
    agg = collections.defaultdict(list); per = []
    for w in ws:
        got = collections.Counter()
        for t in w["turns"]:
            for tr in t["tools"]:
                tg = target(tr)
                if not tg or tr.get("rc") is None: continue
                for k, rx in CAT:
                    if rx.search(tg): got[k] += tr["rc"] / CPT; break
        for k in got: agg[k].append(got[k])
        att = sum(n for p, ty, n in w["start"]["instr"]) / CPT
        per.append(att + got["project rules"] + got["skill text"])
        w["instr_tok"] = att + got["project rules"] + got["skill text"]; w["brief_tok"] = w["start"]["brief"] / CPT + got["CR brief files"]
    cell = lambda k: f"{len(agg[k])} / {st.mean(agg[k])/1e3:.1f}k" if agg[k] else "0"
    print(f"| {wr} | {len(ws)} | {cell('project rules')} | {cell('skill text')} | {cell('CR brief files')} | {st.mean(per)/1e3:.1f}k |")
json.dump({w["meta"]["agent_id"]: [w["instr_tok"], w["brief_tok"]] for w in W}, open(os.path.join(HERE, "..", "..", "data", "A2", "payload.json"), "w"))
# examples of rules files read
ex = collections.Counter()
for w in W:
    if w["wrole"] not in ("coder", "inspector"): continue
    for t in w["turns"]:
        for tr in t["tools"]:
            tg = target(tr)
            if tg and CAT[0][1].search(tg) and tr.get("rc"):
                m = re.search(r"[\w./-]*(AGENTS\.md|CLAUDE\.md|CONTRIBUTING\.md|README\.md|constitution\.md|guidelines/[\w.-]+|glossary/[\w.-]+)", tg)
                ex[(w["wrole"], m.group(1) if m else tg[:50])] += tr["rc"] / CPT
print("\nProject-rule reads, total tokens by file (coder/inspector):")
for k, v in ex.most_common(16): print(f"  {k[0]:10s} {v/1e3:7.1f}k  {k[1]}")
