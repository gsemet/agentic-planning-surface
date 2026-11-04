"""Lever 4: main sessions. Context distribution, compactions, orchestration vs conversation, autocompact simulation."""
import sys, os, statistics as st; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
rows, byid = load()
mains = [r for r in rows if r["meta"].get("main") and "agentic-coding-white-paper" in r["meta"]["project"]]
ORCH_PAT = re.compile(r"orchestrat|driver|stack|CR ?\d{3}|run \d|STATE\.md|ORCHESTRATOR|RUN-BRIEF|changes/(03-)?requests|changes/(04-)?archives|worktree|-wt-\d|gh pr|gh run|gh stack|gh api|ListAgents|TaskOutput|feature-session|claude/projects", re.I)
BACKLOG_PAT = re.compile(r"changes/(02-)?backlog|changes/(01-)?inbox|out/reports/e2e", re.I)
def mclass(t, i):
    ks = [x[0] for x in t["inputs"]]
    kinds = [tool_kind(x) for x in t["tools"]]
    blob = " ".join(x[1] for x in t["tools"])
    if "steer" in ks: return "user message (conversation)"
    if "compact" in ks or "compact_summary" in ks: return "after compaction"
    if "handback" in ks or "task_notif" in ks or "peer_msg" in ks:
        if any(k == "sendmessage" for k in kinds): return "orchestration: relay / steer an agent"
        if any(k == "spawn" for k in kinds): return "orchestration: (re)start agents"
        return "orchestration: react to agent/task notification"
    if any(k == "sendmessage" for k in kinds): return "orchestration: relay / steer an agent"
    if any(k == "spawn" for k in kinds):
        return "orchestration: (re)start agents" if ORCH_PAT.search(blob) else "delegation: spawn helper (research/other)"
    if any(k in ("wait-tool",) for k in kinds) or any(k in ("bash:poll", "bash:sleep") for k in kinds): return "orchestration: monitoring / waiting"
    if any(x[0] in ("Write", "Edit") and x[1].endswith(".py") for x in t["tools"]) or any(x[0] == "Bash" and re.search(r"python3? .*\.py|<<'?(EOF|E|PY)'?", x[1]) and "scratchpad" in x[1] for x in t["tools"]):
        return "orchestration: ad hoc scripts"
    if t["tools"] and BACKLOG_PAT.search(blob) and not ORCH_PAT.search(blob): return "backlog / evidence work (Chief of Staff)"
    if any(x[0] in ("ListAgents",) for x in t["tools"]): return "orchestration: monitoring / waiting"
    if t["tools"] and ORCH_PAT.search(blob):
        if any(k in ("edit-status", "edit-other") for k in kinds) and re.search(r"00-request|01-intent|02-backlog|01-inbox|task\.md|rules\.md", blob): return "CR authoring (backlog/request/brief)"
        if any(k.startswith("bash:git") or k.startswith("bash:gh") for k in kinds): return "orchestration: git/gh status"
        return "orchestration: read/write run state"
    if not t["tools"]: return "reply text only (conversation)"
    if any(k in ("edit-status", "edit-other", "edit-src") for k in kinds): return "direct editing (non-CR files)"
    return "other tool work (research, reading)"
for r in mains:
    T = r["turns"]
    if len(T) < 50: continue
    print(f"\n## main {r['meta']['session']}: turns {len(T)}, ${r['cost']:.2f}, compactions {r['compactions']}, {T[0]['ts'][:16]} -> {T[-1]['ts'][:16]}")
    c = [ctx(t) for t in T]
    print(f"context: median {st.median(c)/1e3:.0f}k mean {st.mean(c)/1e3:.0f}k p90 {sorted(c)[int(.9*len(c))]/1e3:.0f}k max {max(c)/1e3:.0f}k")
    bands = collections.Counter(); bc = collections.Counter()
    for t in T:
        b = "<50k" if ctx(t) < 5e4 else "50-100k" if ctx(t) < 1e5 else "100-150k" if ctx(t) < 1.5e5 else "150-200k" if ctx(t) < 2e5 else "200-300k" if ctx(t) < 3e5 else ">300k"
        bands[b] += 1; bc[b] += t["cost"]
    print("bands:", {b: (bands[b], round(bc[b], 1)) for b in ["<50k", "50-100k", "100-150k", "150-200k", "200-300k", ">300k"]})
    p = PRICE["opus"]
    comp = collections.Counter()
    for t in T:
        comp["read"] += t["cr"] * PRICE[t["fam"]][3] / 1e6; comp["w1h"] += t["w1h"] * PRICE[t["fam"]][2] / 1e6; comp["w5"] += t["w5"] * PRICE[t["fam"]][1] / 1e6; comp["out"] += t["out"] * PRICE[t["fam"]][4] / 1e6
    print("components:", {k: round(v, 1) for k, v in comp.items()})
    # compactions: ctx before/after
    pre = []; post = []
    for i, t in enumerate(T):
        if i and any(x[0] in ("compact", "compact_summary") for x in t["inputs"]):
            pre.append(ctx(T[i - 1])); post.append(ctx(t))
    if pre: print(f"compactions seen at turn level: {len(pre)}; ctx before median {st.median(pre)/1e3:.0f}k, after median {st.median(post)/1e3:.0f}k")
    cl = collections.Counter(); cn = collections.Counter()
    for i, t in enumerate(T):
        k = mclass(t, i); cl[k] += t["cost"]; cn[k] += 1
    tot = sum(cl.values())
    print("| Main-session turn class | Turns | Cost | Share |"); print("| --- | --- | --- | --- |")
    for k, v in cl.most_common(): print(f"| {k} | {cn[k]} | ${v:.2f} | {100*v/tot:.1f}% |")
    orch = sum(v for k, v in cl.items() if k.startswith("orchestration")); conv = sum(v for k, v in cl.items() if "conversation" in k)
    print(f"orchestration total ${orch:.2f} ({100*orch/tot:.0f}%), conversation ${conv:.2f} ({100*conv/tot:.0f}%)")
    # user messages count & incoming notifications
    nu = sum(1 for t in T for x in t["inputs"] if x[0] == "steer"); nh = sum(1 for t in T for x in t["inputs"] if x[0] in ("handback", "task_notif", "peer_msg"))
    print(f"user messages {nu}, agent/task notifications {nh}")
    ep = None; epc = 0; eo = False; res = collections.Counter(); resn = collections.Counter()
    for i, t in enumerate(T + [None]):
        ks = [x[0] for x in t["inputs"]] if t else ["steer"]
        new = "user" if "steer" in ks else "notification" if any(k in ("handback", "task_notif", "peer_msg") for k in ks) else None
        if new:
            if ep: res[(ep, eo)] += epc; resn[(ep, eo)] += 1
            ep, epc, eo = new, 0, False
        if t is None: break
        epc += t["cost"]; eo = eo or mclass(t, i).startswith("orchestration")
    print("episodes (started by, contains orchestration action) -> $, count:", {f"{k[0]}/{'orch' if k[1] else 'no-orch'}": (round(v, 1), resn[k]) for k, v in res.items()})
    # autocompact simulation at 100k
    for CAP, BASE in [(100e3, 45e3), (150e3, 50e3)]:
        sim = 0.0; cur = None; ncomp = 0
        for i, t in enumerate(T):
            fam = PRICE[t["fam"]]; real = ctx(t)
            new = t["w1h"] + t["w5"] + t["in"]
            if i == 0 or rebuild(t, i): grow = min(new, 20e3) if cur is not None else new
            else: grow = new
            if cur is None: cur = real
            else: cur += grow if not rebuild(t, i) else min(grow, 20e3)
            if cur > CAP:
                ncomp += 1
                sim += (cur * fam[3] + 8e3 * fam[4]) / 1e6  # summary call: read context + ~8k output
                cur = BASE
                sim += cur * fam[2] / 1e6  # rewrite the compacted prefix
            reb = rebuild(t, i)
            sim += ((cur - (new if not reb else cur)) * fam[3] + (new if not reb else cur) * fam[2] + t["out"] * fam[4]) / 1e6
        print(f"autocompact sim cap {CAP/1e3:.0f}k base {BASE/1e3:.0f}k: ${sim:.2f} vs actual ${r['cost']:.2f} ({100*(r['cost']-sim)/r['cost']:.0f}% saving), {ncomp} compactions")
