"""Item 2: waits inside the LLM (polls, sleeps, until loops, idle ticks, CI checks) and the residual wake cost."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_sim import *
rows, byid = load_all(); calibrate(rows)
WEEK = 7 / 7.61
def wake_cost(t_wake, S, gapsec, ttl, fam, pi):
    p = PRICE[fam]; w = p[2] if ttl > 300 else p[1]
    if gapsec > ttl: return ((S - pi * PREFIX) * w + pi * PREFIX * p[3]) / 1e6, True
    return S * p[3] / 1e6, False
print("| Role | Variant | Wait turns | Real $ of wait turns | Episodes | Polls/episode med (max) | Episode wall min med / p90 | Wakes after >5 min | Real $ of episodes incl. wake | Design-2 $ 5-min TTL | Design-2 $ 1-h TTL | Saving 5-min | Saving 1-h |")
print("|" + "---|" * 13)
tot = collections.Counter()
for ro in ORCH + ["main"]:
    rs = [r for r in rows if r["role"] == ro]
    for var in ("low", "high"):
        nturn = 0; c_wait = 0.0; eps = []; real_ep = 0.0; d5 = 0.0; d1 = 0.0; nwake5 = 0
        for r in rs:
            T = r["turns"]; n = len(T); pi = PI = prefix_share(r["role"])
            w = [i > 0 and (is_wait_high(r, i) if var == "high" else is_wait_low(T[i])) for i in range(n)]
            i = 0
            while i < n:
                if not w[i]: i += 1; continue
                j = i
                while j + 1 < n and w[j + 1]: j += 1
                k = j + 1  # wake turn
                nturn += j - i + 1; c_wait += sum(T[m]["cost"] for m in range(i, j + 1))
                if k < n:
                    wall = (ts(T[k]["ts"]) - ts(T[i]["ts_last"])).total_seconds()
                    eps.append((j - i + 1, wall))
                    real_ep += sum(T[m]["cost"] for m in range(i, k + 1))
                    # design 2: launch turn i (as real, minus nothing) + wake turn k at context ctx(T[i]) + small result
                    launch = T[i]["cost"]
                    S = ctx(T[i]) + T[i]["out"] + WAIT_RESULT
                    out = T[k]["out"] * PRICE[T[k]["fam"]][4] / 1e6
                    newtok = max(0, ctx(T[k]) - ctx(T[j]) - T[j]["out"])  # what the wake brings in (same as today)
                    c5, rb = wake_cost(T[k], S, wall, 300, T[k]["fam"], pi); nwake5 += rb
                    c1, _ = wake_cost(T[k], S, wall, 3600, T[k]["fam"], pi)
                    p = PRICE[T[k]["fam"]]
                    d5 += launch + c5 + out + newtok * p[1] / 1e6
                    d1 += launch + (T[i]["w5"] + T[i]["w1h"]) * (p[2] - p[1]) / 1e6 + c1 + out + newtok * p[2] / 1e6
                i = j + 1
        if not eps: continue
        pol = [e[0] for e in eps]; wall = [e[1] / 60 for e in eps]
        print(f"| {D2NAME[ro]} | {var} | {nturn} | {c_wait:.2f} | {len(eps)} | {st.median(pol):.0f} ({max(pol)}) | {st.median(wall):.1f} / {pct(wall,.9):.1f} | {nwake5} | {real_ep:.2f} | {d5:.2f} | {d1:.2f} | {real_ep-d5:+.2f} | {real_ep-d1:+.2f} |")
        tot[(var, "real")] += real_ep; tot[(var, "d5")] += d5; tot[(var, "d1")] += d1
for var in ("low", "high"):
    print(f"TOTAL {var}: real episodes ${tot[(var,'real')]:.2f}, design-2 5-min ${tot[(var,'d5')]:.2f} (saving {tot[(var,'real')]-tot[(var,'d5')]:+.2f}), 1-h ${tot[(var,'d1')]:.2f} (saving {tot[(var,'real')]-tot[(var,'d1')]:+.2f}); per week x{WEEK:.2f}")

# Single foreground long waits (one turn that blocks on gh run watch / long sleep): already outside the 'poll' loop
print("\nForeground blocking waits (one Bash call > 5 min) followed by a rebuild:")
for ro in ORCH:
    rs = [r for r in rows if r["role"] == ro]
    n = 0; c = 0.0
    for r in rs:
        T = r["turns"]
        for i in range(1, len(T)):
            g = gap(T, i)
            if g and g > 300 and rebuild(T[i], i) and any(x[0] == "Bash" and not x[2] for x in T[i - 1]["tools"]):
                n += 1; c += write_price(T[i])
    print(f"  {D2NAME[ro]}: {n} rebuilds after a foreground Bash > 5 min, write ${c:.2f}")
# Gaps between turns by trigger (what the agent waited for)
print("\nRebuilds by what woke the agent (trigger of the rebuild turn), write $:")
for ro in ORCH + ["main"]:
    rs = [r for r in rows if r["role"] == ro]; c = collections.Counter(); nn = collections.Counter()
    for r in rs:
        T = r["turns"]
        for i, t in enumerate(T):
            if rebuild(t, i):
                tr = trig(t)
                if tr == "tool_result":
                    k = [tool_kind([x[2][0], x[2][1]]) for x in t["inputs"] if x[0] == "tool_result"]
                    tr = "result of " + (k[0] if k else "?")
                c[tr] += write_price(t); nn[tr] += 1
    print(f"  {D2NAME[ro]}: " + ", ".join(f"{k} {nn[k]} (${v:.2f})" for k, v in c.most_common(8)))
