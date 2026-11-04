"""Per-run what-if: main-session cost during each run, coder rebuild excess, and the sketch's per-CR estimate."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
rows, byid = load()
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "d_lever2.py")).read()
exec(src[src.index("def excess"):src.index("reb = collections")])
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "f_lever4.py")).read()
exec(src[src.index("ORCH_PAT"):src.index("for r in mains:")])
runs = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "runs.json")))
main = byid["dd375646-4450-4e52-a643-89ff1d9e405a"]
WIN = {}
for r in rows:
    if r["run"]:
        for t in r["turns"]:
            a = WIN.setdefault(r["run"], [t["ts"], t["ts"]]); a[0] = min(a[0], t["ts"]); a[1] = max(a[1], t["ts"])
REMOVED = ("Bash: long suite", "Bash: CI watch", "background task notification")
print("| Run | CRs | Subtree $ | Orchestration own $ | Main-session $ in run window (orchestration turns) | Coder/reviewer rebuild excess after long suites/CI $ | All-in $/CR today | Sketch estimate $/CR | Cut |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for run in ["run1", "run2", "run3", "run4/5"]:
    R = runs[run]; n = len(R["crs"]); w0, w1 = WIN[run]
    mo = sum(t["cost"] for i, t in enumerate(main["turns"]) if w0 <= t["ts"] <= w1 and mclass(t, i).startswith("orchestration"))
    ma = sum(t["cost"] for t in main["turns"] if w0 <= t["ts"] <= w1)
    rx = 0.0
    for r in rows:
        if r["run"] != run or r["role"] not in ("coder/writer", "reviewer"): continue
        for i, t in enumerate(r["turns"]):
            if rebuild(t, i) and waited_for(r, i).startswith(REMOVED): rx += excess(t)
    today = R["cost"] + mo
    # sketch: remove 85% of orchestration own cost and 70% of main orchestration, remove coder rebuild excess,
    # add runners (8 per CR x $0.01) and extra rounds (0.3 per CR x $0.55)
    sk = today - 0.85 * R["orch"] - 0.7 * mo - rx + n * 8 * 0.01 + n * 0.3 * 0.55
    print(f"| {run} | {n} | ${R['cost']:.2f} | ${R['orch']:.2f} | ${ma:.2f} (${mo:.2f}) | ${rx:.2f} | ${today/n:.2f} | ${sk/n:.2f} | {100*(today-sk)/today:.0f}% |")
