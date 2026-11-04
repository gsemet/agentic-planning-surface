"""4. Inspector specifics: what it reads, runs, writes; diff-plus-note simulation; verdict schema."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
I = [w for w in W if w["wrole"] == "inspector"]
F = [w for w in I if w["fact"]]
def kind(tr):
    if tr["name"] == "Bash":
        c = strip_cmd(tr.get("cmd", "")); k = bash_kind(tr.get("cmd", ""))
        if re.match(r"^git (diff|show)", c): return "git diff/show"
        if re.search(r"(reports|reviews)/", c) and k == "read-shell": return "round report/review read"
        if re.search(r"(task|rules|00-request|STATE)\.md", c) and k == "read-shell": return "CR brief read"
        if k == "read-shell": return "source/other read (shell)"
        return "bash:" + k
    if tr["name"] == "Read":
        p = tr.get("path", "")
        if re.search(r"\.(png|jpe?g)$", p, re.I): return "screenshot (Read)"
        if re.search(r"(reports|reviews)/", p): return "round report/review read"
        if re.search(r"(task|rules|00-request|STATE)\.md", p): return "CR brief read"
        return "source/other read (Read)"
    if tr["name"] in ("Write", "Edit"): return "write verdict/other"
    return tr["name"]
for label, S in (("all inspectors", I), ("factory inspectors", F)):
    c = collections.Counter(); tk = collections.Counter(); per = collections.Counter()
    for w in S:
        got = set()
        for t in w["turns"]:
            for tr in t["tools"]:
                k = kind(tr); c[k] += 1; tk[k] += (tr.get("rc") or 0) / CPT + tr.get("img", 0) * 1300
                got.add(k)
        for k in got: per[k] += 1
    print(f"\n### {label}: n={len(S)}, cost ${sum(w['cost'] for w in S):.1f}, turns p50 {st.median([len(w['turns']) for w in S]):.0f} p90 {pct([len(w['turns']) for w in S],.9):.0f}, cost/agent p50 ${st.median([w['cost'] for w in S]):.3f} mean ${st.mean([w['cost'] for w in S]):.3f}, last ctx p50 {st.median([ctx(w['turns'][-1]) for w in S])/1e3:.0f}k")
    print("| Tool use | Calls | Agents using it | Result tokens total | per call |")
    print("| --- | --- | --- | --- | --- |")
    for k, v in c.most_common(22): print(f"| {k} | {v} | {per[k]} ({100*per[k]/len(S):.0f}%) | {tk[k]/1e3:.0f}k | {tk[k]/v:.0f} |")
# verdict length
vl = []; hb = []; diffs = []; notes = []
for w in I:
    wl = sum(tr.get("wlen", 0) for t in w["turns"] for tr in t["tools"] if tr["name"] in ("Write",) and re.search(r"review", tr.get("path", ""), re.I))
    wl += sum(len(tr.get("cmd", "")) for t in w["turns"] for tr in t["tools"] if tr["name"] == "Bash" and re.search(r"reviews/", tr.get("cmd", "")) and bash_kind(tr["cmd"]) == "write-shell")
    vl.append(wl / CPT); hb.append(sum(tr.get("hb", 0) for t in w["turns"] for tr in t["tools"]) / CPT)
    diffs.append(sum((tr.get("rc") or 0) for t in w["turns"] for tr in t["tools"] if kind(tr) == "git diff/show") / CPT)
    notes.append(sum((tr.get("rc") or 0) for t in w["turns"] for tr in t["tools"] if kind(tr) == "round report/review read") / CPT)
print(f"\nverdict file tokens p50 {st.median(vl):.0f} p90 {pct(vl,.9):.0f}; hand-back tokens p50 {st.median(hb):.0f} p90 {pct(hb,.9):.0f}")
print(f"diff tokens read per inspector p50 {st.median(diffs):.0f} p90 {pct(diffs,.9):.0f}; coder report read p50 {st.median(notes):.0f}")
out_total = sum(t["out"] for w in I for t in w["turns"]); print(f"inspector output tokens {out_total/1e6:.2f} MTok; verdict+handback text {sum(vl)/1e6+sum(hb)/1e6:.2f} MTok ({100*(sum(vl)+sum(hb))/out_total:.0f}%)")
# simulation: diff-plus-note inspector: base prefix (first ctx) + diff + note + images, 4 turns, output = verdict + 30 %
res = collections.Counter()
for w in I:
    T = w["turns"]; fam = T[0]["fam"]; p = PRICE[fam]
    base = ctx(T[0]); d = sum((tr.get("rc") or 0) for t in T for tr in t["tools"] if kind(tr) == "git diff/show") / CPT
    n = sum((tr.get("rc") or 0) for t in T for tr in t["tools"] if kind(tr) == "round report/review read") / CPT
    imgs = sum(tr.get("img", 0) for t in T for tr in t["tools"]) * 1300
    verdict = (sum(tr.get("wlen", 0) for t in T for tr in t["tools"] if tr["name"] == "Write") + sum(tr.get("hb", 0) for t in T for tr in t["tools"])) / CPT
    out_today = sum(t["out"] for t in T)
    # turns: 1 read diff+note, 1 view images (if any), 1 write verdict, 1 hand-back
    turns = 3 + (1 if imgs else 0)
    ctxs = [base, base + d + n, base + d + n + imgs, base + d + n + imgs + verdict][:turns]
    cost = base * 0.55 * p[3] / 1e6 + base * 0.45 * p[1] / 1e6  # first turn: shared prefix read + rest written
    prev = base
    for c_ in ctxs[1:]: cost += (prev * p[3] + (c_ - prev) * p[1]) / 1e6; prev = c_
    # output: thinking scales with turns; keep today's mean output per turn x turns + verdict
    o = min(out_today, turns * (out_today / len(T)) + verdict)
    cost += o * p[4] / 1e6
    res["today"] += w["cost"]; res["diffnote"] += cost
    res["schema_out"] += max(0, verdict * 0.5) * p[4] / 1e6
    if w["fact"]: res["f_today"] += w["cost"]; res["f_diffnote"] += cost
print(f"\nDiff-plus-note inspector (4 turns, diff+report+images, no source reads, no test runs): ${res['diffnote']:.1f} vs today ${res['today']:.1f} (factory ${res['f_diffnote']:.1f} vs ${res['f_today']:.1f})")
print(f"Verdict schema (verdict+hand-back text halved): saves ${res['schema_out']:.2f} of output")
