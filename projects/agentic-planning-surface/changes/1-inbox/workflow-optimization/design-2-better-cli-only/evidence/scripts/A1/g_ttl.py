"""One-hour TTL for subagents: what it would cost and save, measured on 5-min writes."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
rows, byid = load()
FACT = lambda r: r["run"] is not None or r["ws"] == "CR pipeline before run 1"
for scope_name, sel in [("all subagents", lambda r: not r["meta"].get("main")), ("factory subagents (runs 1-5 + pre-run-1 CR batches)", lambda r: not r["meta"].get("main") and FACT(r))]:
    c = collections.Counter()
    for r in rows:
        if not sel(r): continue
        for i, t in enumerate(r["turns"]):
            p = PRICE[t["fam"]]; w = t["w5"] * p[1] / 1e6
            c["w5$"] += w
            if rebuild(t, i):
                g = gap(r["turns"], i)
                c["reb$"] += w
                if g < 3600: c["reb<1h$"] += w; c["reb<1h_read$"] += t["w5"] * p[3] / 1e6
                else: c["reb>1h$"] += w
            elif i == 0: c["cold$"] += w
            else: c["incr$"] += w
    nonreb = c["cold$"] + c["incr$"]
    extra = 0.6 * nonreb + 0.6 * c["reb>1h$"]
    saved = c["reb<1h$"] - c["reb<1h_read$"]
    print(f"\n{scope_name}: 5-min writes ${c['w5$']:.1f} = cold starts ${c['cold$']:.1f} + incremental ${c['incr$']:.1f} + rebuilds ${c['reb$']:.1f} (gap<1h ${c['reb<1h$']:.1f}, >1h ${c['reb>1h$']:.1f})")
    print(f"  at 1-h TTL (x1.6): non-rebuild writes would cost ${1.6*nonreb:.1f} (+${0.6*nonreb:.1f}); rebuilds <1h become reads (saves ${saved:.1f}); rebuilds >1h cost +${0.6*c['reb>1h$']:.1f}")
    print(f"  NET effect of 1-h TTL: {'+' if extra-saved>0 else ''}${extra-saved:.1f} (positive = more expensive)")
# After levers 1-2: orchestration roles gone; coder/reviewer rebuilds after long suites, CI polls and background waits gone.
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "d_lever2.py")).read()
exec(src[src.index("def waited_for"):src.index("reb = collections")])
REMOVED = ("Bash: long suite", "Bash: CI watch", "background task notification")
c = collections.Counter()
for r in rows:
    if r["meta"].get("main") or r["role"] in ("orchestrator", "driver", "stack driver", "task driver", "integrator"): continue
    for i, t in enumerate(r["turns"]):
        p = PRICE[t["fam"]]; w = t["w5"] * p[1] / 1e6
        if rebuild(t, i):
            wf = waited_for(r, i)
            if wf.startswith(REMOVED): continue
            g = gap(r["turns"], i)
            if g < 3600: c["save"] += w - t["w5"] * p[3] / 1e6
            else: c["extra"] += 0.6 * w
        else:
            c["extra"] += 0.6 * w
print(f"\nAfter levers 1-2 (coder/reviewer/analyst/other only): 1-h TTL extra ${c['extra']:.1f}, saves ${c['save']:.1f}, NET +${c['extra']-c['save']:.1f}")
