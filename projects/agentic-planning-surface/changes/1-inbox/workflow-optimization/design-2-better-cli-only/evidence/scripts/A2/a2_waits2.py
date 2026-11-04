"""2b. Long-suite / CI / bg waits in coders+inspectors: outcome (source edits after = fix needed), and options."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
EV = json.load(open(os.path.join(HERE, "..", "..", "data", "A2", "rebuild_events.json")))
WB = {w["meta"]["agent_id"]: w for w in W}
SRC = re.compile(r"/(src|test|tests|scripts|media|e2e)/|\.(ts|tsx|js|mjs|css|py)\b")
def src_edit(tr):
    if tr["name"] in ("Edit", "Write", "NotebookEdit"): return bool(SRC.search(tr.get("path", ""))) and not re.search(r"/(reports|reviews)/|\.md$", tr.get("path", ""))
    if tr["name"] == "Bash":
        c = tr.get("cmd", "")
        return bash_kind(c) == "write-shell" and bool(SRC.search(c)) and not re.search(r"reports/|reviews/", c)
    return False
def grp(wf):
    if wf.startswith("Bash: long suite"): return "long"
    if wf.startswith("Bash: CI watch"): return "ci"
    if wf == "background task notification": return "bg"
    return None
sel = [e for e in EV if e["wr"] in ("coder", "inspector") and grp(e["wf"])]
for e in sel:
    w = WB[e["aid"]]; T = w["turns"]; i = e["i"]
    e["src_after"] = any(src_edit(tr) for u in T[i:] for tr in u["tools"])
    # cost of the coder from the rebuild turn to its end (what (c) removes on a pass)
    e["tail_turns"] = len(T) - i
    # later long suites in the same agent
    e["more_suites"] = sum(1 for u in T[i:] for tr in u["tools"] if tr["name"] == "Bash" and bash_kind(tr["cmd"]) == "gate-long")
print("| Role | Wait | Events | Excess $ | Pass (no source edit after) | Fail -> fix in same agent | Excess on pass | Excess on fail | Tail cost after pass event, mean (turns) | Median ctx |")
print("|" + " --- |" * 10)
for wr in ("coder", "inspector"):
    for k in ("long", "ci", "bg"):
        v = [e for e in sel if e["wr"] == wr and grp(e["wf"]) == k]
        if not v: continue
        p = [e for e in v if not e["src_after"]]; f = [e for e in v if e["src_after"]]
        print(f"| {wr} | {k} | {len(v)} | ${sum(e['ex'] for e in v):.2f} | {len(p)} | {len(f)} | ${sum(e['ex'] for e in p):.2f} | ${sum(e['ex'] for e in f):.2f} | ${st.mean([e['tail'] for e in p]) if p else 0:.2f} ({st.mean([e['tail_turns'] for e in p]) if p else 0:.1f}) | {st.median([e['ctx'] for e in v])/1e3:.0f}k |")
json.dump(sel, open(os.path.join(HERE, "..", "..", "data", "A2", "wait_events.json"), "w"))
# durations of long suites (fg) in coders/inspectors: tool ts -> result ts
d = collections.defaultdict(list); bgw = []
for w in W:
    if w["wrole"] not in ("coder", "inspector"): continue
    for t in w["turns"]:
        for tr in t["tools"]:
            if tr["name"] == "Bash" and tr.get("rts"):
                k = bash_kind(tr["cmd"])
                dur = (ts(tr["rts"]) - ts(tr["ts"])).total_seconds()
                if not tr.get("bg"): d[k].append(dur)
print("\nForeground Bash wall time (tool call -> result), coders+inspectors:")
for k in ("gate-long", "gate-fast", "poll", "ui-drive", "okfreq", "read-shell"):
    v = sorted(d[k]); n = len(v)
    if n: print(f"  {k:10s} n={n:5d} p50 {v[n//2]:6.0f}s p75 {v[int(.75*(n-1))]:6.0f}s p90 {v[int(.9*(n-1))]:6.0f}s  >300s {sum(1 for x in v if x>300)}  300-600s {sum(1 for x in v if 300<=x<600)}  >600s {sum(1 for x in v if x>=600)}")
# Monitor/TaskOutput waits
mw = []
for w in W:
    if w["wrole"] not in ("coder", "inspector"): continue
    for t in w["turns"]:
        for tr in t["tools"]:
            if tr["name"] in ("Monitor", "TaskOutput", "BashOutput") and tr.get("rts"):
                mw.append((ts(tr["rts"]) - ts(tr["ts"])).total_seconds())
mw.sort(); n = len(mw)
if n: print(f"  Monitor/TaskOutput calls n={n} p50 {mw[n//2]:.0f}s p90 {mw[int(.9*(n-1))]:.0f}s >300s {sum(1 for x in mw if x>300)}")
# background launches: what happened between launch and notification
