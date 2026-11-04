"""7. Combined per-role saving, sequential (overlap-aware) simulation on real turns; per-CR effect on runs 1-3."""
import sys, os, glob, base64, struct; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
D = os.path.join(HERE, "..", "..", "data", "A2")
EV = json.load(open(os.path.join(D, "wait_events.json"))); FR = json.load(open(os.path.join(D, "fresh_ref.json")))
EVA = collections.defaultdict(list)
for e in EV: EVA[e["aid"]].append(e)
exec(open(os.path.join(HERE, "a2_images.py")).read().split("want = {")[0].split("from wcommon import *")[1])  # dims/toks/paths helpers
RULES = re.compile(r"(AGENTS|CLAUDE|CONTRIBUTING|README)\.md|constitution|\.agents/guidelines/|\.agents/glossary|guideline|skills/[^ ]*(SKILL\.md|references/)")
PATHRX = re.compile(r"\.(ts|tsx|js|mjs|json|md|py|css|html|yml|yaml|sh|txt)\b")
def is_whole(tr):
    if tr["name"] == "Read": return not (tr.get("off") or tr.get("lim"))
    if tr["name"] == "Bash":
        c = strip_cmd(tr.get("cmd", "")); return bool(re.match(r"^cat\b", c)) and "|" not in c[:200] and bool(PATHRX.search(c))
    return False
def is_read(tr):
    if tr["name"] in ("Read", "Grep", "Glob"): return True
    return tr["name"] == "Bash" and bash_kind(tr.get("cmd", "")) == "read-shell"
DRV = 0.148
STUDIO_AGENTS = 5332 / CPT
def wait_saving(w, e, scen):
    kind = "long" if e["wf"].startswith("Bash: long") else "ci" if e["wf"].startswith("Bash: CI") else "bg"
    T = w["turns"]; i = e["i"]
    if scen == "low":   # (c) driver runs long suites and CI; resume the same coder on failure
        return (e["ex"] - DRV) if not e["src_after"] else -DRV
    # high: (d) long suites under 4-5 min -> no rebuild at all; CI/bg -> (c) with fresh coder + note on failure
    if kind == "long": return e["ex"]
    if not e["src_after"]: return e["ex"] - DRV
    fam = T[i]["fam"]; pre = 0.22 if fam == "sonnet" else 0.62
    delta = max(0, e["ctx"] - FR["2"]["ctx_med"])
    tail_today = sum(t["cost"] for t in T[i:])
    tail_fresh = sum(max(0.0, t["cost"] - min(delta, t["cr"]) * PRICE[t["fam"]][3] / 1e6) for t in T[i + 1:])
    return max(-DRV, tail_today - (0.5 * pre + tail_fresh) - DRV)
def resume_saving(w, scen):
    if w["wrole"] not in ("coder", "writer (req)", "inspector", "critic (req)"): return 0.0
    T = w["turns"]; hb = [i for i, t in enumerate(T) if any(tr["name"] == "SubagentHandback" for tr in t["tools"])]
    j = next((k for k, t in enumerate(T) if any(tr["name"] in ("Edit", "Write") or (tr["name"] == "Bash" and bash_kind(tr.get("cmd", "")) == "write-shell") for tr in t["tools"])), min(len(T) - 1, 5))
    explore = sum(t["cost"] for t in T[:j]); s = 0.0
    for h in hb:
        i = h + 1
        if i >= len(T) or gap(T, i) < 300: continue
        nxt = [x for x in hb if x > h]; end = nxt[0] + 1 if nxt else len(T)
        seg = T[i:end]; delta = max(0, ctx(T[i]) - ctx(T[j]))
        fresh = 0.5 * explore + sum(max(0.0, t["cost"] - min(delta, t["cr"]) * PRICE[t["fam"]][3] / 1e6) for t in seg[1:])
        s += sum(t["cost"] for t in seg) - fresh
    return s * (0.5 if scen == "low" else 1.0)
img_cache = {}
def img_info(w):
    aid = w["meta"]["agent_id"]
    if not any(tr.get("img") for t in w["turns"] for tr in t["tools"]): return {}
    info = {}
    with open(paths[aid], errors="replace") as f:
        for line in f:
            if '"image"' not in line: continue
            d = json.loads(line)
            for b in (d.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_result" and isinstance(b.get("content"), list):
                    for x in b["content"]:
                        if isinstance(x, dict) and x.get("type") == "image":
                            dd = dims((x.get("source") or {}).get("data") or "")
                            if dd: info.setdefault(b.get("tool_use_id"), []).append(dd)
    return info
paths = {os.path.basename(p)[6:-6]: p for p in glob.glob(os.path.expanduser("~/.claude/projects/*/*/subagents/*.jsonl"))}
R = collections.defaultdict(collections.Counter); PER = {}
for w in W:
    s = w["start"]; wr = w["wrole"]; rp = result_pos(w); T = w["turns"]
    art = s["toolsizes"].get("Artifact", 0) / CPT; sk = s["att"].get("skill_listing", 0) / CPT
    extra = sum(s["toolsizes"].get(k, 0) for k in ("Agent", "ListAgents", "ReportFindings")) / CPT
    wp = max(0, sum(n for p, ty, n in s["instr"] if "agentic-coding-white-paper/AGENTS.md" in p or "MEMORY.md" in p) / CPT - STUDIO_AGENTS)
    pos0 = ctx(T[0]) - s["brief"] / CPT
    card = [(0, pos0, s["brief"] / CPT)]; tgt = []; cap = []; imgc = []
    ii = img_info(w)
    for t in T:
        for tr in t["tools"]:
            if tr["id"] not in rp or tr.get("rc") is None: continue
            j, pos = rp[tr["id"]]; tok = tr["rc"] / CPT
            g = tr.get("path", "") if tr["name"] == "Read" else strip_cmd(tr.get("cmd", ""))[:400] if tr["name"] == "Bash" else ""
            if g and RULES.search(g) and is_read(tr): card.append((j, pos, tok)); continue
            if is_whole(tr) and tok > 3000: tgt.append((j, pos, tok * 0.7))
            elif tr["name"] == "Bash" and not is_read(tr) and tok > 1000: cap.append((j, pos, tok - 1000))
            for (a, b) in ii.get(tr["id"], []): imgc.append((j, pos, max(0, toks(a, b) - toks(a, b, 800))))
    out = {}
    for scen in ("low", "high"):
        pre = art + sk + wp + (extra if scen == "high" else 0)
        f_card = 0.3 if scen == "low" else 0.5; f_rd = 0.5 if scen == "low" else 1.0
        cuts = [(0, 0, pre)] + [(a, b, c * f_card) for a, b, c in card] + [(a, b, c * f_rd) for a, b, c in tgt + cap]
        if scen == "high": cuts += imgc
        s123 = cut_saving(w, cuts)
        comp = {"prefix": cut_saving(w, [(0, 0, pre)])}
        scale = max(0.0, 1 - s123 / w["cost"]) if w["cost"] else 1
        sw = sum(wait_saving(w, e, scen) * (1 - pre / max(e["ctx"], 1)) for e in EVA.get(w["meta"]["agent_id"], []))
        sr = resume_saving(w, scen) * scale
        tot = s123 + sw + sr
        R[(wr, scen)]["cuts"] += s123; R[(wr, scen)]["prefix"] += comp["prefix"]; R[(wr, scen)]["waits"] += sw; R[(wr, scen)]["resume"] += sr; R[(wr, scen)]["tot"] += tot
        out[scen] = tot
    R[(wr, "x")]["cost"] += w["cost"]; R[(wr, "x")]["fact"] += w["cost"] if w["fact"] else 0
    for scen in ("low", "high"): R[(wr, scen)]["fact"] += out[scen] if w["fact"] else 0
    PER[w["meta"]["agent_id"]] = out
# hand-over note on round-2+ coders
base = FR["2"]["n"] * FR["2"]["cost_pre_mean"] + FR["3"]["n"] * FR["3"]["cost_pre_mean"]
R[("coder", "low")]["tot"] += 0.25 * base; R[("coder", "high")]["tot"] += 0.5 * base; R[("coder", "low")]["note"] = 0.25 * base; R[("coder", "high")]["note"] = 0.5 * base
print("| Role | Window cost | Prefix (tools, skill list, AGENTS.md) | + role card, reads, caps, images | Waits (low: c + resume; high: d + c + fresh) | Resume rule + hand-over note | Total window low–high | Per week low–high | % of role |")
print("|" + " --- |" * 9)
TT = collections.Counter()
for wr in WROLES:
    c = R[(wr, "x")]["cost"]; L = R[(wr, "low")]; H = R[(wr, "high")]
    for k in ("tot",): TT["low"] += L[k]; TT["high"] += H[k]
    TT["cost"] += c
    print(f"| {wr} | ${c:.1f} | ${L['prefix']:.1f}–{H['prefix']:.1f} | ${L['cuts']-L['prefix']:.1f}–{H['cuts']-H['prefix']:.1f} | ${L['waits']:.1f}–{H['waits']:.1f} | ${L['resume']+L['note']:.1f}–{H['resume']+H['note']:.1f} | ${L['tot']:.1f}–{H['tot']:.1f} | ${0.92*L['tot']:.0f}–{0.92*H['tot']:.0f} | {100*L['tot']/c:.0f}–{100*H['tot']/c:.0f} % |")
print(f"| all workers | ${TT['cost']:.1f} | | | | | ${TT['low']:.1f}–{TT['high']:.1f} | ${0.92*TT['low']:.0f}–{0.92*TT['high']:.0f} | {100*TT['low']/TT['cost']:.0f}–{100*TT['high']/TT['cost']:.0f} % |")
f = collections.Counter()
for wr in WROLES: f["cost"] += R[(wr, "x")]["fact"]; f["low"] += R[(wr, "low")]["fact"]; f["high"] += R[(wr, "high")]["fact"]
print(f"factory-scope workers: cost ${f['cost']:.1f}, saving ${f['low']:.1f}–{f['high']:.1f} (excl. hand-over note)")
# per CR, runs 1-3
def cr_for(aid):
    r = byid[aid]
    for d in [r["desc"]] + [byid[a]["desc"] for a in r["ancestors"] if a in byid]:
        c = cr_of(d)
        if c: return c
    return None
ALLIN = {"run1": (17, 6.93), "run2": (7, 4.86), "run3": (3, 3.72)}
print("\n| Run | CRs | Worker cost/CR | Saving/CR low–high | All-in $/CR today | Cut of all-in |")
print("| --- | --- | --- | --- | --- | --- |")
for run, (n, allin) in ALLIN.items():
    ws = [w for w in W if w["run"] == run]
    c = sum(w["cost"] for w in ws); lo = sum(PER[w["meta"]["agent_id"]]["low"] for w in ws); hi = sum(PER[w["meta"]["agent_id"]]["high"] for w in ws)
    print(f"| {run} | {n} | ${c/n:.2f} | ${lo/n:.2f}–{hi/n:.2f} | ${allin:.2f} | {100*lo/n/allin:.0f}–{100*hi/n/allin:.0f} % |")
