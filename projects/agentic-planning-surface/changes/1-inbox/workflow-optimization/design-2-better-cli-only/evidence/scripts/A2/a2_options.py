"""2c. Options (a)-(d) for coder/inspector waits, simulated event by event on real turns."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
D = os.path.join(HERE, "..", "..", "data", "A2")
EV = json.load(open(os.path.join(D, "wait_events.json"))); FR = json.load(open(os.path.join(D, "fresh_ref.json")))
WB = {w["meta"]["agent_id"]: w for w in W}
drv = [ctx(t) for r in rows if r["role"] == "driver" and r["run"] for t in r["turns"]]
DCTX = st.median(drv); print(f"driver ctx p50 in runs 1-5: {DCTX/1e3:.0f}k (p90 {pct(drv,.9)/1e3:.0f}k)")
DRV_EVENT = (DCTX * (2.5 - 0.2) + 2 * DCTX * 0.2 + 2 * 400 * 10) / 1e6  # one rebuild + 2 warm turns + ~400 out tok x2, Sonnet
print(f"driver cost per long-gate event (Sonnet, rebuild after a >5 min wait, 2 turns): ${DRV_EVENT:.3f}")
def suite_dur(w, i):
    t = w["turns"][i - 1]; ds = [(ts(tr["rts"]) - ts(tr["ts"])).total_seconds() for tr in t["tools"] if tr["name"] == "Bash" and tr.get("rts")]
    return max(ds) if ds else 0
fresh_pre = {"sonnet": (0.18, 0.22), "opus": (0.57, 0.62)}
res = collections.defaultdict(collections.Counter)
for e in EV:
    w = WB[e["aid"]]; T = w["turns"]; i = e["i"]; k = e["wf"]; wr = e["wr"]
    kind = "long" if k.startswith("Bash: long") else "ci" if k.startswith("Bash: CI") else "bg"
    key = (wr, kind); R = res[key]
    R["n"] += 1; R["excess"] += e["ex"]; R["pass"] += not e["src_after"]
    # (a) background + notify: gap unchanged -> rebuild unchanged
    R["a"] += 0.0
    # (c) driver runs the long suite / CI
    if not e["src_after"]:
        R["c_pass_save"] += e["ex"]; R["c_drv"] += DRV_EVENT
    else:
        # c1: resume same coder -> same rebuild + driver turns
        R["c1_fail_save"] += -DRV_EVENT; R["c_drv"] += DRV_EVENT
        # c2: fresh coder: exploration cost + rest of tail with smaller ctx
        fam = T[i]["fam"]; lo, hi = fresh_pre[fam]
        delta = max(0, e["ctx"] - FR["2"]["ctx_med"])
        tail_today = sum(t["cost"] for t in T[i:])
        tail_fresh = sum(max(0.0, t["cost"] - min(delta, t["cr"]) * PRICE[t["fam"]][3] / 1e6) for t in T[i + 1:])
        for lab, pre in (("lo", lo), ("hi", hi)):
            R["c2_fail_save_" + lab] += tail_today - (pre + tail_fresh) - DRV_EVENT
    # (d) shorter suites
    dur = suite_dur(w, i)
    for f in (0.5, 0.33):
        if e["gap"] - (1 - f) * dur < 300: R[f"d{f}"] += e["ex"]
    if e["gap"] - max(0, dur - 240) < 300: R["d_cap4"] += e["ex"]
print("\n| Role / wait | Events | Excess today | Pass | (a) bg+notify | (c) pass: rebuild avoided | (c) driver cost | (c1) fail, resume coder | (c2) fail, fresh coder (Sonnet/Opus pre-edit low-high) | (d) suite x0.5 | (d) suite x0.33 | (d) suite capped 4 min |")
print("|" + " --- |" * 12)
tot = collections.Counter()
for key in sorted(res):
    R = res[key]
    for kk in R: tot[kk] += R[kk]
    print(f"| {key[0]} {key[1]} | {R['n']} | ${R['excess']:.2f} | {R['pass']} | ${R['a']:.2f} | ${R['c_pass_save']:.2f} | -${R['c_drv']:.2f} | ${R['c1_fail_save']:.2f} | ${R['c2_fail_save_hi']:.2f} … ${R['c2_fail_save_lo']:.2f} | ${R['d0.5']:.2f} | ${R['d0.33']:.2f} | ${R['d_cap4']:.2f} |")
R = tot
print(f"| total | {R['n']} | ${R['excess']:.2f} | {R['pass']} | $0 | ${R['c_pass_save']:.2f} | -${R['c_drv']:.2f} | ${R['c1_fail_save']:.2f} | ${R['c2_fail_save_hi']:.2f} … ${R['c2_fail_save_lo']:.2f} | ${R['d0.5']:.2f} | ${R['d0.33']:.2f} | ${R['d_cap4']:.2f} |")
fact = [e for e in EV if WB[e["aid"]]["fact"]]
print(f"\nfactory-scope share of these events: {len(fact)} events, excess ${sum(e['ex'] for e in fact):.2f}")
