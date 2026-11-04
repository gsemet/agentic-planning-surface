"""Lever 3: tool-result sizes, how long they are carried, context growth, fresh coder per round."""
import sys, os, statistics as st; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
rows, byid = load()
CPT = 3.2
FACT = lambda r: r["run"] is not None or r["ws"] == "CR pipeline before run 1"
def rkind(x):
    name, short = x[2][0], x[2][1]
    if x[2][3]: return "image"
    if name == "Bash":
        k = bash_kind(short)
        return {"read-shell": "shell read (cat/sed/grep/ls)", "write-shell": "shell write/edit", "gate-long": "long suite output", "gate-fast": "fast gate output",
                "git-read": "git", "git-write": "git", "git-worktree": "git", "gh-ci": "gh / CI", "gh-read": "gh / CI", "gh-pr-write": "gh / CI", "gh-stack": "gh / CI", "poll": "gh / CI",
                "okfreq": "okfreq / requirements"}.get(k, "other shell")
    if name == "Read": return "Read tool"
    if name in ("Grep", "Glob"): return "Grep/Glob"
    if name in ("Agent", "Task"): return "subagent result"
    if name in ("Edit", "Write"): return "Edit/Write ack"
    return "other tool"
res = collections.defaultdict(lambda: collections.Counter())
model_cr = collections.Counter(); meas_cr = collections.Counter()
cap_save = collections.defaultdict(float)
CAP = 1000  # tokens kept for a summarised output (~30 lines)
for r in rows:
    if r["meta"].get("main"): continue
    ro = "coder/writer" if r["role"] == "coder/writer" else "reviewer" if r["role"] == "reviewer" else "other subagents"
    T = r["turns"]; N = len(T)
    for i, t in enumerate(T):
        p = PRICE[t["fam"]]
        meas_cr[ro] += t["cr"] * p[3] / 1e6
        for x in t["inputs"]:
            if x[0] != "tool_result": continue
            tok = x[1] / CPT; carry = N - 1 - i
            k = rkind(x)
            c = tok * (p[1] + carry * p[3]) / 1e6
            a = res[(ro, k)]; a["n"] += 1; a["tok"] += tok; a["carry"] += carry; a["cost"] += c; a["read$"] += tok * carry * p[3] / 1e6
            if FACT(r): a["fact$"] += c
            model_cr[ro] += tok * carry * p[3] / 1e6
            if k in ("long suite output", "fast gate output", "git", "gh / CI", "other shell", "okfreq / requirements", "shell write/edit") and tok > CAP:
                s = (tok - CAP) * (p[1] + carry * p[3]) / 1e6
                cap_save[(ro, k)] += s; cap_save[(ro, "ALL")] += s
                if FACT(r): cap_save[(ro, "FACT")] += s
            if k == "shell read (cat/sed/grep/ls)" and tok > 3 * CAP:
                s = (tok - 3 * CAP) * (p[1] + carry * p[3]) / 1e6
                cap_save[(ro, "shell-read>3k")] += s
                if FACT(r): cap_save[(ro, "shell-read>3k FACT")] += s
for ro in ["coder/writer", "reviewer", "other subagents"]:
    print(f"\n### {ro}: measured cache reads ${meas_cr[ro]:.1f}, modelled tool-result rereads ${model_cr[ro]:.1f} ({100*model_cr[ro]/meas_cr[ro]:.0f}%)")
    print("| Result type | Calls | Avg tokens | Avg turns carried | Cost (write + rereads) | of which factory scope |"); print("| --- | --- | --- | --- | --- | --- |")
    ks = sorted([k for (r_, k) in res if r_ == ro], key=lambda k: -res[(ro, k)]["cost"])
    for k in ks:
        a = res[(ro, k)]
        print(f"| {k} | {a['n']} | {a['tok']/a['n']:.0f} | {a['carry']/a['n']:.0f} | ${a['cost']:.1f} | ${a['fact$']:.1f} |")
    print(f"cap non-read shell/git/gh/gate outputs at {CAP} tok: saves ${cap_save[(ro,'ALL')]:.1f} (factory ${cap_save[(ro,'FACT')]:.1f}); by kind:",
          {k: round(v, 1) for (r_, k), v in cap_save.items() if r_ == ro and k not in ("ALL", "FACT")})
# context growth and turns
print("\n### Context per role (subagents)")
print("| Role | Agents | Median turns | Median first ctx | Median last ctx | Median growth | Mean ctx/turn |"); print("| --- | --- | --- | --- | --- | --- | --- |")
for ro in ROLES:
    rs = [r for r in rows if r["role"] == ro and len(r["turns"]) > 1]
    if not rs: continue
    f = [ctx(r["turns"][0]) for r in rs]; l = [ctx(r["turns"][-1]) for r in rs]
    allc = [ctx(t) for r in rs for t in r["turns"]]
    print(f"| {ro} | {len(rs)} | {st.median([len(r['turns']) for r in rs]):.0f} | {st.median(f)/1e3:.0f}k | {st.median(l)/1e3:.0f}k | {st.median([b/a for a,b in zip(f,l)]):.1f}x | {sum(allc)/len(allc)/1e3:.0f}k |")
# fresh coder per round: round>=2 coders vs round-1, exploration before first edit
def is_edit(x):
    if x[0] in ("Edit", "Write", "NotebookEdit"): return bool(re.search(r"/(src|test|scripts|requirements)/|\.ts$|\.py$", x[1]))
    if x[0] == "Bash": return bash_kind(x[1]) == "write-shell" and re.search(r"src/|test/|\.ts", x[1]) is not None
    return False
def rnd(d):
    m = re.search(r"round[- ]?(\d)|\br(\d)\b|round (\d)", d.lower()) or re.search(r"round-(\d)", d.lower())
    return int(next(g for g in m.groups() if g)) if m else None
print("\n### Coders: exploration before the first source edit, by round (all coder agents with a round in the description)")
grp = collections.defaultdict(list)
for r in rows:
    if r["role"] != "coder/writer" or not re.search(r"coder|implement", r["desc"].lower()): continue
    k = rnd(r["desc"])
    if k is None: continue
    T = r["turns"]; j = next((i for i, t in enumerate(T) if any(is_edit(x) for x in t["tools"])), None)
    if j is None: continue
    pre = sum(t["cost"] for t in T[:j]); hb = sum(1 for t in T for x in t["tools"] if x[0] == "SubagentHandback")
    grp[min(k, 3)].append((pre, j, r["cost"], ctx(T[0]), ctx(T[-1]), hb, len(T)))
print("| Round | Coders | Median turns before first edit | Median $ before first edit | Mean $ before first edit | Median total $ | Median first ctx | Median last ctx | Coders resumed after a hand-back |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for k in sorted(grp):
    v = grp[k]
    print(f"| {k}{'+' if k==3 else ''} | {len(v)} | {st.median([x[1] for x in v]):.0f} | ${st.median([x[0] for x in v]):.2f} | ${st.mean([x[0] for x in v]):.2f} | ${st.median([x[2] for x in v]):.2f} | {st.median([x[3] for x in v])/1e3:.0f}k | {st.median([x[4] for x in v])/1e3:.0f}k | {sum(1 for x in v if x[5]>1)} |")
# kept-alive coders (multiple handbacks): cost after first handback
ka = [(r, [i for i, t in enumerate(r["turns"]) if any(x[0] == "SubagentHandback" for x in t["tools"])]) for r in rows if r["role"] in ("coder/writer", "reviewer", "analyst")]
ka = [(r, h) for r, h in ka if len(h) > 1]
after = sum(sum(t["cost"] for t in r["turns"][h[0] + 1:]) for r, h in ka)
print(f"\nAgents resumed after a hand-back (>1 SubagentHandback): {len(ka)}; cost after their first hand-back ${after:.1f}; turns after {sum(len(r['turns'])-h[0]-1 for r,h in ka)}")
for r, h in sorted(ka, key=lambda x: -x[0]["cost"])[:8]:
    print("   ", r["meta"]["agent_id"], r["desc"][:45], r["role"], f"${r['cost']:.2f}", "handbacks", len(h), "turns", len(r["turns"]))
