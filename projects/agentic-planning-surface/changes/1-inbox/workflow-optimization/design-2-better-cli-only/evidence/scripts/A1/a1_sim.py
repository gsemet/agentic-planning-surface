"""Turn-level simulator for design-2 levers on orchestration roles (Foreman, Driver variants).
Each lever is a transformation of the REAL turn sequence of each agent: drop turns, cap tokens that
enter the context, rotate/compact at a cap, change TTL or model. The cost of every kept turn is
recomputed from its simulated context S_i:
  first turn or gap > TTL  -> write S_i (cold or rebuild)
  else                     -> read S_prev + write max(0, S_i - S_prev)
  + output tokens (+ uncached input).
Validation: the baseline simulation (no lever, 5-min TTL) is compared with the real billed cost."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_common import *

WAIT_KINDS = {"bash:poll", "bash:sleep", "wait-tool"}
MECH_LOW = {"mechanical: git/gh", "mechanical: status/table write"}
MECH_HIGH = MECH_LOW | {"mechanical: reads/other shell", "mechanical: gates"}
CRF_RESULT = 400      # tokens of a crf call result (20-30 lines)
WAIT_RESULT = 150     # tokens of a crf wait result (event line)

def kinds(t): return [tool_kind(x) for x in t["tools"]]

def is_wait_low(t):
    k = kinds(t); return bool(k) and all(x in WAIT_KINDS for x in k)

def is_wait_high(r, i):
    t = r["turns"][i]; k = kinds(t)
    if not k: return False
    if all(x in WAIT_KINDS | {"bash:gh-ci"} for x in k): return True
    # tick with nothing to do: woken by a background bash (sleep) and only status reads / gh checks, then re-arms
    ks = [x[0] for x in t["inputs"]]
    tick_trig = any(x[0] == "task_notif" and re.search(r"<task-id>b", x[2] or "") for x in t["inputs"]) or \
                any(x[0] == "tool_result" and tool_kind([x[2][0], x[2][1]]) in WAIT_KINDS for x in t["inputs"])
    quiet = all(x in WAIT_KINDS | {"bash:gh-ci", "bash:gh-read", "bash:git-read", "read-status", "bash:read-shell"} for x in k)
    if tick_trig and quiet and "handback" not in ks and "steer" not in ks:
        if i + 1 < len(r["turns"]) and (is_wait_low(r["turns"][i + 1]) or any(x[2] and "sleep" in x[1] for x in r["turns"][i + 1]["tools"])): return True
    return False

def plan(r, lv):
    """Return keep[], capnext[] (cap on the delta that turn i's call adds), shrink[] (tokens removed at turn i)."""
    T = r["turns"]; n = len(T)
    keep = [True] * n; capnext = [None] * n; shrink = [0.0] * n; tag = [""] * n
    # Lever 2: waits outside the LLM
    if lv.get("waits"):
        w = [i > 0 and (is_wait_high(r, i) if lv["waits"] == "high" else is_wait_low(T[i])) for i in range(n)]
        i = 0
        while i < n:
            if w[i]:
                j = i
                while j + 1 < n and w[j + 1]: j += 1
                capnext[i] = WAIT_RESULT; tag[i] = "wait-launch"
                for m in range(i + 1, j + 1): keep[m] = False; tag[m] = "wait-dropped"
                i = j + 1
            else: i += 1
    # Lever 3: mechanical runs collapsed into one crf call
    if lv.get("mech"):
        cls = MECH_HIGH if lv["mech"] == "high" else MECH_LOW
        minrun = 2 if lv["mech"] == "high" else 3
        m = [i > 0 and keep[i] and tag[i] == "" and category(r, i) in cls for i in range(n)]
        i = 0
        while i < n:
            if m[i]:
                j = i
                while j + 1 < n and (m[j + 1] or not keep[j + 1]): j += 1
                run = [k for k in range(i, j + 1) if keep[k]]
                if len(run) >= minrun:
                    capnext[run[0]] = CRF_RESULT; tag[run[0]] = "crf-call"
                    for k in run[1:]: keep[k] = False; tag[k] = "mech-dropped"
                i = j + 1
            else: i += 1
    # Lever 4a/4b: caps on what enters the context
    for i, t in enumerate(T):
        if i == 0: continue
        for x in t["inputs"]:
            c = input_class(x); tok = in_tokens(x)
            if lv.get("handback") and c in ("hand-back report", "peer message") and tok > lv["handback"]:
                shrink[i] += tok - lv["handback"]
            if lv.get("status") and c in ("status read", "git/gh status output") and tok > lv["status"]:
                shrink[i] += tok - lv["status"]
    return keep, capnext, shrink, tag

PREFIX = 19700  # shared system+tools prefix often kept warm by sibling agents [M]
_PI = {}
def prefix_share(role, rows=None):
    """Share of real rebuilds where the shared prefix was still cached (cr >= 15k) [M]."""
    return _PI.get(role, 0.0)
def calibrate(rows):
    for ro in set(r["role"] for r in rows):
        rb = [t["cr"] >= 15000 for r in rows if r["role"] == ro for i, t in enumerate(r["turns"]) if rebuild(t, i)]
        _PI[ro] = sum(rb) / len(rb) if rb else 0.5

def simulate(r, lv, ttl=300, fam=None, cap=None, mode="rotate", tick=False):
    T = r["turns"]; n = len(T); pi = _PI.get(r["role"], 0.0)
    keep, capnext, shrink, tag = plan(r, lv)
    B = ctx(T[0])  # base context of a fresh agent (instructions + brief)
    removed = 0.0; S_prev = None; last_end = None; cost = 0.0; nkept = 0; rot = 0; comp_writes = 0.0
    out_rate = None; ticks_n = [0]
    for i, t in enumerate(T):
        f = fam or t["fam"]; p = PRICE[f]
        wprice = p[2] if ttl > 300 else p[1]
        d_next = (ctx(T[i + 1]) - ctx(t)) if i + 1 < n else 0
        if not keep[i]:
            removed += max(0, d_next) if not is_compact(T[i + 1] if i + 1 < n else t) else 0
            continue
        removed += shrink[i]
        if is_compact(t) and i > 0:
            removed = 0.0
        S = max(B * 0.5, ctx(t) - removed)
        g = None if last_end is None else (ts(t["ts"]) - last_end).total_seconds()
        if i == 0 and not fam:
            c = (t["cost"] - t["out"] * p[4] / 1e6 - t["in"] * p[0] / 1e6) * 1e6   # real cold start
            if ttl > 300: c += (t["w5"] + t["w1h"]) * (p[2] - p[1])
        elif tick and g is not None and g > ttl and not (is_compact(t) and i > 0) and S_prev is not None:
            # keep-warm ticks: a background sleep slightly under the TTL wakes the agent, which re-arms it
            nt = int(g // (ttl - 30)); grow = 0.0; c = 0.0
            for _ in range(nt):
                c += (S_prev + grow) * p[3] + 250 * wprice + 100 * p[4] * 1e0; grow += 250
            removed -= grow; S = S + grow; ticks_n[0] += nt
            c += S_prev * p[3] + max(0.0, S - S_prev) * wprice
        elif S_prev is None or g is None or g > ttl or (is_compact(t) and i > 0):
            c = (S - pi * PREFIX) * wprice + pi * PREFIX * p[3]
        else:
            c = S_prev * p[3] + max(0.0, S - S_prev) * wprice
        cost += (c + t["out"] * p[4] + t["in"] * p[0]) / 1e6; nkept += 1
        S_prev = S; last_end = ts(t["ts_last"])
        if capnext[i] is not None and i + 1 < n:
            removed += max(0.0, d_next - t["out"] - capnext[i])
        # rotation / compaction at a context cap
        if cap and S > cap:
            if mode == "rotate":   # handover note, then a fresh Foreman reads crf status
                H = 1500 + 8000   # handover note + re-read of skill/brief (measured ~2.7 reads x 3k tokens per Foreman)
                cost += (S * p[3] + 800 * wprice + 800 * p[4]) / 1e6          # write the handover
                Snew = B + H
                cost += (Snew * wprice + 300 * p[4] + 3 * (B + 4000) * p[3] + 600 * p[4]) / 1e6   # cold start + 3 re-read turns
            else:                  # auto-compaction: summary of ~3.7k tokens, then cold restart of the prefix
                cost += (S * p[3] + 3700 * p[4]) / 1e6
                Snew = B + 3700
                cost += Snew * wprice / 1e6
            removed += S - Snew; S_prev = Snew; rot += 1
    return cost, nkept, rot

def real(r): return sum(t["cost"] for t in r["turns"])

if __name__ == "__main__":
    rows, byid = load_all(); calibrate(rows)
    groups = collections.OrderedDict((ro, [r for r in rows if r["role"] == ro]) for ro in ORCH)
    WEEK = 7 / 7.61
    print("## Validation: baseline simulation vs real billed cost")
    print("| Role | Agents | Real $ | Sim baseline 5-min $ | ratio |"); print("|---|---|---|---|---|")
    for ro, rs in groups.items():
        R = sum(real(r) for r in rs); S = sum(simulate(r, {})[0] for r in rs)
        print(f"| {D2NAME[ro]} | {len(rs)} | {R:.2f} | {S:.2f} | {S/R:.2f} |")
    scen = [
        ("0 baseline (5-min TTL)", {}, 300, None),
        ("L2 waits low", {"waits": "low"}, 300, None),
        ("L2 waits high", {"waits": "high"}, 300, None),
        ("L2 waits high + 1h TTL", {"waits": "high"}, 3600, None),
        ("L2+L3 low", {"waits": "low", "mech": "low"}, 300, None),
        ("L2+L3 high", {"waits": "high", "mech": "high"}, 300, None),
        ("L2+L3+L4ab low (hb 600, status 800)", {"waits": "low", "mech": "low", "handback": 600, "status": 800}, 300, None),
        ("L2+L3+L4ab high (hb 300, status 400)", {"waits": "high", "mech": "high", "handback": 300, "status": 400}, 300, None),
    ]
    print("\n## Sequential levers, all orchestration agents (window, $)")
    hdr = "| Scenario | " + " | ".join(D2NAME[ro] for ro in ORCH) + " | Total | turns kept |"
    print(hdr); print("|" + "---|" * (len(ORCH) + 3))
    for name, lv, ttl, fam in scen:
        vals = []; tot = 0; nk = 0
        for ro, rs in groups.items():
            v = 0
            for r in rs:
                c, k, _ = simulate(r, lv, ttl, fam); v += c; nk += k
            vals.append(v); tot += v
        print(f"| {name} | " + " | ".join(f"{v:.2f}" for v in vals) + f" | {tot:.2f} | {nk} |")
