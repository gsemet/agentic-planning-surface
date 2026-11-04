"""Lever 2: cache rebuilds, gap before them, and what the agent waited for."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
rows, byid = load()
def excess(t):
    p = PRICE[t["fam"]]; return (t["w5"] * (p[1] - p[3]) + t["w1h"] * (p[2] - p[3])) / 1e6
def gb(g): return "<5min" if g < 300 else "5-15min" if g < 900 else "15-60min" if g < 3600 else ">1h"
def waited_for(r, i):
    t = r["turns"][i]; prev = r["turns"][i - 1]
    k = trig(t)
    if k in ("steer",): return "message from main/user" if not r["meta"].get("main") else "user prompt"
    if k == "handback": return "subagent hand-back (background)"
    if k == "task_notif": return "background task notification"
    if k == "peer_msg": return "peer message"
    if k in ("compact", "compact_summary"): return "compaction"
    kinds = [tool_kind(x) for x in prev["tools"]]
    if any(x == "spawn" for x in kinds): return "foreground subagent"
    if any(x == "tool:SubagentHandback" for x in kinds): return "resumed after its own hand-back (kept alive)"
    if [x for x in prev["tools"] if x[0] == "Bash"]:
        cmds = " ; ".join(strip_cmd(x[1]) for x in prev["tools"] if x[0] == "Bash")
        if re.search(r"gh (run|pr checks)|until|while .*sleep|sleep \d|wait\.sh|--watch", cmds): return "Bash: CI watch / poll loop"
        if re.search(r"just (visual|ci-|preflight)|test:integration|test:stress|integration|visual|stress|e2e|gate\.sh|finish\.sh|run-tests|capture", cmds): return "Bash: long suite (visual/integration/preflight/window)"
        if re.search(r"just check|test:unit|npm (run )?test|tsc|vitest|mocha|just test", cmds): return "Bash: fast gates (just check / unit)"
    if any(x == "wait-tool" for x in kinds): return "wait tool (TaskOutput/Monitor)"
    b = [x[5:] for x in kinds if x.startswith("bash:")]
    for pri in ["gate-long", "ui-drive", "poll", "gh-ci", "sleep", "gate-fast", "okfreq", "node", "python", "git-write", "git-read", "gh-read", "write-shell", "read-shell", "sys", "other"]:
        if pri in b: return "Bash " + pri
    return "other tool: " + ",".join(sorted(set(kinds)))[:40]
reb = collections.defaultdict(lambda: collections.Counter())
gaps = collections.defaultdict(lambda: collections.Counter())
wf = collections.defaultdict(lambda: collections.Counter())
samples = collections.defaultdict(list)
for r in rows:
    ro = r["role"]
    for i, t in enumerate(r["turns"]):
        if not rebuild(t, i): continue
        g = gap(r["turns"], i); b = gb(g)
        reb[ro]["n"] += 1; reb[ro]["write$"] += write_price(t); reb[ro]["excess$"] += excess(t)
        gaps[ro][b + "|n"] += 1; gaps[ro][b + "|$"] += excess(t)
        w = waited_for(r, i)
        wf[ro][w + "|n"] += 1; wf[ro][w + "|$"] += excess(t); wf[ro][w + "|" + b] += 1
        if ro in ("coder/writer", "reviewer") and len(samples[w]) < 6:
            prev = r["turns"][i - 1]
            samples[w].append((r["meta"]["agent_id"], r["desc"][:40], int(g), [strip_cmd(x[1])[:90].replace("\n", " ") for x in prev["tools"]]))
T = sum(v["excess$"] for v in reb.values())
print("| Role | Rebuilds | Rebuild write $ | Excess over warm read $ | <5min | 5-15min | 15-60min | >1h |"); print("| --- | --- | --- | --- | --- | --- | --- | --- |")
for ro in ROLES:
    if ro not in reb: continue
    g = gaps[ro]
    print(f"| {ro} | {reb[ro]['n']} | ${reb[ro]['write$']:.1f} | ${reb[ro]['excess$']:.1f} | " + " | ".join(f"{g[b+'|n']} (${g[b+'|$']:.1f})" for b in ["<5min", "5-15min", "15-60min", ">1h"]) + " |")
print(f"total excess ${T:.1f}, total write ${sum(v['write$'] for v in reb.values()):.1f}")
for ro in ["coder/writer", "reviewer", "analyst", "main"]:
    print(f"\n### What {ro} rebuilds waited for")
    print("| Waited for | Rebuilds | Excess $ | <5min | 5-15 | 15-60 | >1h |"); print("| --- | --- | --- | --- | --- | --- | --- |")
    w = wf[ro]
    for k in sorted({x.split("|")[0] for x in w}, key=lambda k: -w[k + "|$"]):
        print(f"| {k} | {w[k+'|n']} | ${w[k+'|$']:.2f} | {w[k+'|<5min']} | {w[k+'|5-15min']} | {w[k+'|15-60min']} | {w[k+'|>1h']} |")
print("\nSamples (coder/reviewer):")
for k, v in samples.items():
    print("==", k)
    for s in v[:4]: print("   ", s)
# Duration of single-Bash turns by kind (measured wall time until next turn), coders/reviewers
dur = collections.defaultdict(list)
for r in rows:
    if r["role"] not in ("coder/writer", "reviewer"): continue
    ts_ = r["turns"]
    for i in range(len(ts_) - 1):
        t = ts_[i]
        if len(t["tools"]) == 1 and t["tools"][0][0] == "Bash" and not t["tools"][0][2]:
            nxt = ts_[i + 1]
            if trig(nxt) != "tool_result": continue
            d = (ts(nxt["ts"]) - ts(t["ts_last"])).total_seconds()
            dur[bash_kind(t["tools"][0][1])].append(d)
print("\nForeground Bash durations in coders/reviewers (s): kind n p50 p90 share>300s")
for k, v in sorted(dur.items(), key=lambda x: -len(x[1])):
    v.sort(); n = len(v)
    print(f"  {k:12s} {n:6d} p50 {v[n//2]:7.0f} p90 {v[int(.9*(n-1))]:7.0f} >300s {sum(1 for x in v if x>300)}")
