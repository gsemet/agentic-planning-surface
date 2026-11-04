"""3. Context levers: read shapes and sizes, same-file re-reads, targeted-read and output-cap simulations."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
PATHRX = re.compile(r"((?:/|\./|~/)?[\w@.+-]+(?:/[\w@.+-]+)*\.(?:ts|tsx|js|mjs|cjs|json|md|py|css|html|yml|yaml|sh|txt|toml|svg|feature|jsonl))")
def classify(tr):
    if tr["name"] == "Read":
        return ("Read range" if (tr.get("off") or tr.get("lim")) else "Read whole", tr.get("path"))
    if tr["name"] in ("Grep", "Glob"): return ("Grep/Glob tool", None)
    if tr["name"] != "Bash": return (None, None)
    c = strip_cmd(tr.get("cmd", "")); k = bash_kind(tr.get("cmd", ""))
    if k != "read-shell": return (None, None)
    m = PATHRX.search(c); p = m.group(1) if m else None
    if re.match(r"^cat\b", c) and "|" not in c.split("\n")[0][:200]: return ("cat whole", p)
    if re.match(r"^cat\b", c): return ("cat | filter", p)
    if re.match(r"^(sed -n|sed -E -n|awk)", c): return ("sed -n range", p)
    if re.match(r"^(head|tail)", c): return ("head/tail", p)
    if re.match(r"^(grep|egrep|rg|/usr/bin/grep)", c): return ("grep", p)
    if re.match(r"^(ls|find|tree|du|stat|file|wc)", c): return ("ls/find/wc", None)
    if re.match(r"^(diff|jq|cut|nl)", c): return ("diff/jq/other", p)
    return ("other read", p)
res = collections.defaultdict(collections.Counter); sizes = collections.defaultdict(list)
rer = collections.defaultdict(collections.Counter)
sim = collections.defaultdict(collections.Counter)
CAPS = {"targeted (whole-file reads >3k tok -> 30 %)": None}
for w in W:
    wr = w["wrole"]; rp = result_pos(w)
    seen = {}  # path -> (turn, tokens)
    edited = collections.defaultdict(int)  # path -> last edit turn
    dup_cuts = []; tgt_cuts = []; cap_cuts = []
    for j, t in enumerate(w["turns"]):
        for tr in t["tools"]:
            if tr["name"] in ("Edit", "Write") and tr.get("path"): edited[os.path.basename(tr["path"])] = j
            if tr["name"] == "Bash" and bash_kind(tr.get("cmd", "")) == "write-shell":
                for m in PATHRX.finditer(tr.get("cmd", "")): edited[os.path.basename(m.group(1))] = j
            if tr.get("rc") is None or tr["id"] not in rp: continue
            tok = tr["rc"] / CPT; i0, pos = rp[tr["id"]]
            k, p = classify(tr)
            if k:
                res[wr][k + "|n"] += 1; res[wr][k + "|tok"] += tok; sizes[(wr, k)].append(tok)
                if k in ("cat whole", "Read whole") and tok > 3000: tgt_cuts.append((i0, pos, tok * 0.7))
                if p and k in ("cat whole", "Read whole", "Read range", "sed -n range", "head/tail", "cat | filter"):
                    b = os.path.basename(p)
                    if b in seen:
                        rer[wr]["re-reads"] += 1; rer[wr]["re-read tok"] += tok
                        if edited.get(b, -1) < seen[b][0]:
                            rer[wr]["unchanged re-reads"] += 1; rer[wr]["unchanged tok"] += tok
                            if k in ("cat whole", "Read whole"): dup_cuts.append((i0, pos, tok))
                    seen[b] = (j, tok)
                    rer[wr]["file reads"] += 1
            else:
                # non-read outputs: cap at 1000 tokens (~30 lines)
                if tr["name"] == "Bash" and tok > 1000: cap_cuts.append((i0, pos, tok - 1000))
            if tr.get("img"):
                res[wr]["images|n"] += tr["img"]; res[wr]["images|b64"] += tr["b64"]
    sim[wr]["targeted"] += cut_saving(w, tgt_cuts); sim[wr]["dedupe unchanged whole re-reads"] += cut_saving(w, dup_cuts)
    sim[wr]["cap non-read output 1k"] += cut_saving(w, cap_cuts); sim[wr]["cost"] += w["cost"]
KS = ["cat whole", "Read whole", "Read range", "sed -n range", "head/tail", "cat | filter", "grep", "Grep/Glob tool", "ls/find/wc", "diff/jq/other", "other read"]
for wr in ("coder", "inspector", "writer (req)", "critic (req)", "analyst (req)"):
    R = res[wr]
    print(f"\n### {wr}: read calls by shape (count, mean tokens, p90, share of read tokens)")
    tot = sum(R[k + "|tok"] for k in KS)
    for k in KS:
        if R[k + "|n"]: print(f"  {k:16s} n={R[k+'|n']:5d} mean {R[k+'|tok']/R[k+'|n']:6.0f} p90 {pct(sizes[(wr,k)],.9):6.0f} share {100*R[k+'|tok']/tot:4.1f}%")
    Q = rer[wr]
    print(f"  same-file re-reads: {Q['re-reads']} of {Q['file reads']} file reads ({100*Q['re-reads']/max(1,Q['file reads']):.0f}%), {Q['re-read tok']/1e6:.2f} MTok; unchanged since last read: {Q['unchanged re-reads']} ({Q['unchanged tok']/1e6:.2f} MTok)")
    print(f"  images: {R['images|n']} , mean base64 {R['images|b64']/max(1,R['images|n'])/1e3:.0f} kB")
print("\n| Role | Cost | Targeted reads (whole-file reads >3k tok cut to 30 %) | Dedupe unchanged whole-file re-reads | Cap non-read Bash output at 1k tok |")
print("| --- | --- | --- | --- | --- |")
for wr in WROLES:
    S = sim[wr]; print(f"| {wr} | ${S['cost']:.1f} | ${S['targeted']:.2f} | ${S['dedupe unchanged whole re-reads']:.2f} | ${S['cap non-read output 1k']:.2f} |")
