"""Item 8: combined per-role and total weekly saving (levers applied sequentially), and per-CR cost for runs 1-3."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_sim import *
rows, byid = load_all(); calibrate(rows)
WEEK = 7 / 7.61
LOW = {"waits": "low", "mech": "low", "handback": 600, "status": 800}
HIGH = {"waits": "high", "mech": "high", "handback": 300, "status": 400}
CFG = {"low": (LOW, 3600, None, 150e3, False), "high": (HIGH, 3600, None, 100e3, True)}
def sim(r, k, fam=None):
    lv, ttl, _, cap, tick = CFG[k]; return simulate(r, lv, ttl, fam, cap, "rotate", tick)[0]
print("## Final configuration per role ($ window → $ week)")
print("| Role | Real | Design 2 low-saving case | Design 2 high-saving case | Saving/week | + Sonnet everywhere (high case) |"); print("|---|---|---|---|---|---|")
TOT = collections.Counter()
for ro in ORCH:
    rs = [r for r in rows if r["role"] == ro]
    R = sum(real(r) for r in rs); L = sum(sim(r, "low") for r in rs); H = sum(sim(r, "high") for r in rs); HS = sum(sim(r, "high", "sonnet") for r in rs)
    TOT["R"] += R; TOT["L"] += L; TOT["H"] += H; TOT["HS"] += HS
    print(f"| {D2NAME[ro]} | {R:.2f} | {L:.2f} | {H:.2f} | {(R-L)*WEEK:.1f}–{(R-H)*WEEK:.1f} | {HS:.2f} |")
print(f"| **All orchestration roles** | {TOT['R']:.2f} | {TOT['L']:.2f} | {TOT['H']:.2f} | {(TOT['R']-TOT['L'])*WEEK:.1f}–{(TOT['R']-TOT['H'])*WEEK:.1f} | {TOT['HS']:.2f} |")
# per run
WIN = {}
for r in rows:
    if r["run"]:
        for t in r["turns"]:
            a = WIN.setdefault(r["run"], [t["ts"], t["ts"]]); a[0] = min(a[0], t["ts"]); a[1] = max(a[1], t["ts"])
NCR = {"run1": 17, "run2": 7, "run3": 3}
main = [r for r in rows if r["role"] == "main"][0]
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "f_lever4.py")).read()
exec(src[src.index("ORCH_PAT"):src.index("for r in mains:")])
MAIN_RATIO = {"low": 42.60 / 84.91, "high": 0.95}   # from a7_main.py: simulated saving / orchestration-turn cost (high capped at 95%)
print("\n## Per CR, runs 1-3 (orchestration roles + main-session orchestration in the run window; coders/reviewers unchanged)")
print("| Run | CRs | Subtree $ today | of which orchestration own $ | Main orch. turns in window $ | All-in $/CR today | Orchestration own $ design 2 (low–high) | Main orch. $ design 2 (low–high) | All-in $/CR design 2 | Cut |")
print("|---|---|---|---|---|---|---|---|---|---|")
SPLIT = "2026-10-27T16:32:09"   # design-1: a21e1ec0 counts for run 3 only before its first CR 135 spawn
for r in rows:
    if r["meta"]["agent_id"] == "a21e1ec0a8fc37d31":
        r3 = dict(r); r3["turns"] = [t for t in r["turns"] if t["ts"] < SPLIT]; r["_r3"] = r3
for run in ("run1", "run2", "run3"):
    rs = [r.get("_r3", r) if run == "run3" else r for r in rows if r["run"] == run]; n = NCR[run]
    sub = sum(real(r) for r in rs); orch = [r for r in rs if r["role"] in ORCH]; oR = sum(real(r) for r in orch)
    oL = sum(sim(r, "low") for r in orch); oH = sum(sim(r, "high") for r in orch)
    w0, w1 = WIN[run]
    mo = sum(t["cost"] for i, t in enumerate(main["turns"]) if w0 <= t["ts"] <= w1 and mclass(t, i).startswith("orchestration"))
    mL = mo * (1 - MAIN_RATIO["low"]); mH = mo * (1 - MAIN_RATIO["high"])
    today = (sub + mo) / n; dL = (sub - oR + oL + mL) / n; dH = (sub - oR + oH + mH) / n
    print(f"| {run} | {n} | {sub:.2f} | {oR:.2f} | {mo:.2f} | {today:.2f} | {oL:.2f}–{oH:.2f} | {mL:.2f}–{mH:.2f} | {dL:.2f}–{dH:.2f} | {100*(1-dL/today):.0f}–{100*(1-dH/today):.0f}% |")
