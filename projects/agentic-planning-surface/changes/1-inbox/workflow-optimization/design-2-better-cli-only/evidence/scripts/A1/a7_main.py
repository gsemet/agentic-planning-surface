"""Item 7: why the main session did orchestration, the design-2 fix per cause, and what remains."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_sim import *
rows, byid = load_all(); calibrate(rows)
WEEK = 7 / 7.61
M = [r for r in rows if r["role"] == "main"][0]; T = M["turns"]
# --- design-1 f_lever4.py turn classes (copied) ---
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
# ---
FORGE_W = re.compile(r"gh pr (merge|edit|ready|create)|gh run (rerun|cancel)|gh workflow run|git (rebase|push|merge|reset|cherry-pick|commit)|gh stack (sync|push|rebase)|worktree remove|branch -D", re.I)
STATUS_R = re.compile(r"STATE\.md|ORCHESTRATOR|STACK-STATE|TASKS\.md|gh pr (view|list|checks)|gh run (view|list|watch)|git (log|status|branch)|ListAgents|TaskOutput", re.I)
ORCH_AGENT = re.compile(r"orchestr|driver|stack|integrat|land|restart|resume|supervis|rebase|foreman", re.I)
def src_role(x):
    m = re.search(r'from="(a[0-9a-f]+)"', x[2] or "") or re.search(r"<task-id>(a[0-9a-f]+)</task-id>", x[2] or "")
    if not m: return "bash" if re.search(r"<task-id>b", x[2] or "") else "?"
    a = byid.get(m.group(1)); return a["role"] if a else "?"
def ep_trigger(t):
    for x in t["inputs"]:
        if x[0] == "steer":
            s = (x[2] or "").lower()
            if re.search(r"\bmerg|mergé|j'ai mergé|merged", s): return "user: merged"
            if re.fullmatch(r"\s*(continue|contineu|continu|go|vas-y|reprends|ok|yes|oui)\W*\s*", s[:40]): return "user: continue"
            if len(s) < 160 and re.search(r"etat|état|alors|status|statut|où en|ou en|bloqu|en cours|progress|still running|stuck|agents? (en cours|running)|is it|where are|\?\s*$", s): return "user: status question"
            return "user: content"
    for x in t["inputs"]:
        if x[0] in ("handback", "peer_msg", "task_notif"):
            sr = src_role(x)
            if sr in ORCH: return f"notification from {sr}"
            if sr == "bash": return "notification: background shell"
            return "notification: other agent"
    return None
def turn_cause(t):
    kinds_ = [tool_kind(x) for x in t["tools"]]; blob = " ".join(x[1] for x in t["tools"])
    names = [x[0] for x in t["tools"]]
    if "TaskStop" in names or any(x[0] in ("Agent", "Task") and ORCH_AGENT.search(x[1]) for x in t["tools"]): return "restart / (re)start agents"
    if "SendMessage" in names: return "relay / steer an agent"
    if any(x[0] in ("Write", "Edit") and x[1].endswith(".py") for x in t["tools"]) or any(x[0] == "Bash" and re.search(r"python3? .*\.py|<<'?(EOF|E|PY)'?", x[1]) and ORCH_PAT.search(x[1]) for x in t["tools"]): return "ad hoc scripts"
    if FORGE_W.search(blob): return "child work: merge/rebase/land/CI rerun"
    if any(k in ("bash:poll", "bash:sleep", "wait-tool") for k in kinds_) or "ListAgents" in names: return "monitoring / waiting"
    if t["tools"] and (STATUS_R.search(blob) or ORCH_PAT.search(blob)): return "status read / run state"
    return None
# episodes
eps = []; cur = None
for i, t in enumerate(T):
    tr = ep_trigger(t)
    if tr: cur = {"trig": tr, "turns": [i]}; eps.append(cur)
    elif cur: cur["turns"].append(i)
    else: cur = {"trig": "(start)", "turns": [i]}; eps.append(cur)
tab = collections.defaultdict(lambda: [0, 0, 0.0, 0, 0.0])  # episodes, turns, cost, orch turns, orch cost
cause = collections.defaultdict(lambda: [0, 0.0]); cause_by_trig = collections.defaultdict(collections.Counter)
orch_turn = [False] * len(T); CAUSE = [None] * len(T); WHY = [None] * len(T)
for e in eps:
    a = tab[e["trig"]]; a[0] += 1
    for i in e["turns"]:
        t = T[i]; a[1] += 1; a[2] += t["cost"]
        c = None
        if mclass(t, i).startswith("orchestration"):
            c = turn_cause(t) or ("react to factory notification (read, no action)" if e["trig"].startswith("notification") else "status read / run state")
        if c:
            CAUSE[i] = c; a[3] += 1; a[4] += t["cost"]; cause[c][0] += 1; cause[c][1] += t["cost"]; cause_by_trig[e["trig"]][c] += t["cost"]; orch_turn[i] = True
print(f"## Main session {MAIN_ID}: {len(T)} turns, ${M['cost']:.2f}, {len(eps)} episodes")
print("\n| Episode trigger | Episodes | Turns | Cost | Orchestration turns | Orchestration $ |"); print("|---|---|---|---|---|---|")
for k, a in sorted(tab.items(), key=lambda kv: -kv[1][4]):
    print(f"| {k} | {a[0]} | {a[1]} | ${a[2]:.2f} | {a[3]} | ${a[4]:.2f} |")
print("\n| Turn cause | Turns | Cost |"); print("|---|---|---|")
for k, a in sorted(cause.items(), key=lambda kv: -kv[1][1]): print(f"| {k} | {a[0]} | ${a[1]:.2f} |")
print(f"orchestration total: {sum(a[0] for a in cause.values())} turns ${sum(a[1] for a in cause.values()):.2f}")
print("\nCause x trigger ($):")
for trg, c in cause_by_trig.items(): print(f"  {trg}: " + ", ".join(f"{k} {v:.2f}" for k, v in c.most_common()))
# notifications received by source role
src = collections.Counter()
for t in T:
    for x in t["inputs"]:
        if x[0] in ("handback", "peer_msg", "task_notif"): src[(x[0], src_role(x))] += 1
print("\nnotifications by (kind, source role):", dict(src.most_common()))
# Freeze / non-delivery evidence: user 'continue' and status questions, TaskStop count
print("TaskStop calls:", sum(1 for t in T for x in t["tools"] if x[0] == "TaskStop"),
      "| orchestration Agent spawns:", sum(1 for t in T for x in t["tools"] if x[0] in ("Agent", "Task") and ORCH_AGENT.search(x[1])),
      "| SendMessage:", sum(1 for t in T for x in t["tools"] if x[0] == "SendMessage"))

# ---- Design-2 simulation of the main session (Chief of Staff)
# keep[i] False for orchestration turns that the Foreman/crf takes over; residual turns: 1 per user-status or merge episode
def plan_main(var):
    keep = [True] * len(T); capnext = [None] * len(T)
    for e in eps:
        idx = [i for i in e["turns"] if orch_turn[i]]
        if not idx: continue
        trig_ = e["trig"]
        if trig_.startswith("notification from") or trig_ == "notification: background shell":
            # Foreman notifies only on decisions/run end: low keeps the episode's first turn, high drops it unless it relays a user decision
            if var == "low": idx = idx[1:]
        elif trig_ in ("user: status question", "user: merged", "user: continue"):
            capnext[idx[0]] = CRF_RESULT; idx = idx[1:]   # one crf status / crf note call
        else:  # user content with orchestration: keep relay/decision turns, drop status reads, monitoring, child work, scripts
            keepc = ("relay / steer an agent",) if var == "high" else ("relay / steer an agent", "restart / (re)start agents", "ad hoc scripts")
            idx = [i for i in idx if CAUSE[i] not in keepc]
            if idx and var == "low": capnext[idx[0]] = CRF_RESULT; idx = idx[1:]
        for i in idx: keep[i] = False
    return keep, capnext
def sim_main(keep, capnext, cap=None, ttl=3600, tick=False):
    removed = 0.0; S_prev = None; last_end = None; cost = 0.0; B = 45000; ncomp = 0
    for i, t in enumerate(T):
        p = PRICE[t["fam"]]; w = p[2]
        d_next = (ctx(T[i + 1]) - ctx(t)) if i + 1 < len(T) else 0
        if not keep[i]:
            if i + 1 < len(T) and not is_compact(T[i + 1]): removed += max(0, d_next)
            continue
        if is_compact(t): removed = 0.0
        S = max(30000, ctx(t) - removed)
        g = None if last_end is None else (ts(t["ts"]) - last_end).total_seconds()
        if tick and S_prev is not None and g > ttl and not is_compact(t):
            nt = int(g // (ttl - 30)); c = sum((S_prev + 250 * k) * p[3] + 250 * w + 100 * p[4] for k in range(nt)); removed -= 250 * nt; S += 250 * nt
            c += S_prev * p[3] + max(0, S - S_prev) * w
        elif S_prev is None or g > ttl or is_compact(t): c = S * w
        else: c = S_prev * p[3] + max(0, S - S_prev) * w
        cost += (c + t["out"] * p[4] + t["in"] * p[0]) / 1e6; S_prev = S; last_end = ts(t["ts_last"])
        if capnext[i] is not None: removed += max(0, d_next - t["out"] - capnext[i])
        if cap and S > cap:
            cost += (S * p[3] + 3700 * p[4]) / 1e6; Snew = B; cost += Snew * w / 1e6; removed += S - Snew; S_prev = Snew; ncomp += 1
    return cost, ncomp
base, _ = sim_main([True] * len(T), [None] * len(T))
print(f"\n## Design-2 simulation of {MAIN_ID} (Opus, 1-h TTL)\nsim baseline ${base:.2f} vs real ${M['cost']:.2f}")
for var in ("low", "high"):
    keep, capnext = plan_main(var)
    c, _ = sim_main(keep, capnext)
    print(f"{var}: drop {keep.count(False)} turns -> ${c:.2f} (saving ${base-c:.2f}, {100*(base-c)/base:.0f}%)")
    for cap in (100e3, 150e3, 200e3):
        c2, nc = sim_main(keep, capnext, cap)
        print(f"   + autocompact at {int(cap/1e3)}k: ${c2:.2f} ({nc} compactions; extra saving ${c-c2:.2f})")
for var, cap in (("low", 150e3), ("high", 100e3)):
    keep, capnext = plan_main(var)
    a, _ = sim_main(keep, capnext, cap); b, _ = sim_main(keep, capnext, cap, tick=True)
    print(f"final {var} (autocompact {int(cap/1e3)}k): ${a:.2f}; with keep-warm /loop tick every 59.5 min while idle: ${b:.2f} ({b-a:+.2f})")
b0, _ = sim_main([True] * len(T), [None] * len(T), None, tick=True)
print(f"keep-warm alone on today's session: ${b0:.2f} vs ${base:.2f} ({b0-base:+.2f})")
# per-cause saving: drop only that cause's turns
print("\nSaving per cause, simulated alone (drop that cause's turns; 1 crf call kept per user status/merge episode):")
for cz in sorted(cause, key=lambda k: -cause[k][1]):
    keep = [not (orch_turn[i] and CAUSE[i] == cz) for i in range(len(T))]
    c, _ = sim_main(keep, [None] * len(T))
    print(f"  {cz}: ${base-c:.2f}")
# weekly cost of the remaining main session per week
print(f"\nweek factor {WEEK:.3f}")

# ---- WHY: one cause per episode (priority order), orchestration turns only
STALL_U = re.compile(r"bloqu|stuck|froze|fig[ée]|0 agents|pas bloqu|toujours rien|nothing happen|still running|is it running|tourne|dead|mort|contin", re.I)
NUDGE = re.compile(r"stuck|still|status\?|are you|blocked|froze|nudge|reply|respond|alive|did you|have you|restart|resume|re-?send|not received|waiting for your", re.I)
why = collections.defaultdict(lambda: [0, 0, 0.0])
for e in eps:
    idx = [i for i in e["turns"] if orch_turn[i]]
    if not idx: continue
    tools = [x for i in e["turns"] for x in T[i]["tools"]]
    utext = " ".join((x[2] or "") for x in T[e["turns"][0]]["inputs"] if x[0] == "steer")
    stall = any(x[0] == "TaskStop" for x in tools) or any(x[0] in ("Agent", "Task") and re.search(r"orchestr|restart|resume|replac|driver", x[1], re.I) and re.search(r"restart|resume|replac|relaunch|new orchestr|\bF2\b|\bJ\b", x[1], re.I) for x in tools) \
        or any(x[0] == "SendMessage" and NUDGE.search(x[1]) for x in tools) or (e["trig"].startswith("user") and STALL_U.search(utext[:200]))
    tr = e["trig"]
    if stall: w = "A Foreman/agent stalled, froze, died, or a message did not land (nudge, TaskStop, restart)"
    elif tr == "user: status question": w = "B User asked for status"
    elif tr == "user: merged": w = "C Merge / landing follow-up"
    elif tr.startswith("notification from"): w = "D Report from a factory agent (orchestrator/driver hand-back, interim report)"
    elif tr == "notification: background shell": w = "E Main session's own waits: CI / heavy CI / bisect run in background shells"
    elif tr == "notification: other agent": w = "F Main session acted as orchestrator (coders/reviewers/analysts it launched itself)"
    elif tr.startswith("user"): w = "G User decision or new work → relay, brief, open CRs, then check state"
    else: w = "H other"
    a = why[w]; a[0] += 1; a[1] += len(idx); a[2] += sum(T[i]["cost"] for i in idx)
    for i in idx: WHY[i] = w
print("\n## WHY the main session did orchestration (one cause per episode; orchestration turns only)")
print("| Cause | Episodes | Orch. turns | Orch. $ (window) | Saving if removed, simulated alone |"); print("|---|---|---|---|---|")
for w in sorted(why):
    keep = [not (orch_turn[i] and WHY[i] == w) for i in range(len(T))]
    c, _ = sim_main(keep, [None] * len(T))
    a = why[w]; print(f"| {w} | {a[0]} | {a[1]} | ${a[2]:.2f} | ${base-c:.2f} |")
