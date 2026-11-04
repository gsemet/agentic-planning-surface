"""Item 3: mechanical turns collapsed into crf calls. What is dropped, per role and per CR."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_sim import *
rows, byid = load_all(); calibrate(rows)
def crf_cmd(kinds):
    k = set(kinds)
    if k & {"bash:gh-stack"}: return "crf stack"
    if k & {"bash:git-worktree"}: return "crf open/land (worktree)"
    if k & {"bash:git-write", "bash:gh-pr-write"}: return "crf ship (commit/push/PR)"
    if k & {"bash:gate-long", "bash:gate-fast", "bash:okfreq"}: return "crf gate"
    if k & {"edit-status", "bash:write-shell"}: return "crf set / render"
    if k & {"bash:gh-ci", "bash:gh-read"}: return "crf ci / pr status"
    if k & {"bash:git-read"}: return "crf status (git)"
    return "crf status (files)"
for var in ("low", "high"):
    lv = {"waits": var, "mech": var}
    print(f"\n## L3 {var}: turns replaced by crf calls")
    print("| Role | crf calls | Turns dropped | Turns per call (incl. the call) | Real $ of dropped turns | by command (calls/dropped) |")
    print("|---|---|---|---|---|---|")
    for ro in ORCH:
        rs = [r for r in rows if r["role"] == ro]
        calls = 0; dropped = 0; dc = 0.0; bycmd = collections.Counter(); byd = collections.Counter()
        for r in rs:
            keep, capnext, shrink, tag = plan(r, lv); T = r["turns"]
            i = 0
            while i < len(T):
                if tag[i] == "crf-call":
                    j = i + 1; ks = kinds(T[i])
                    while j < len(T) and tag[j] in ("mech-dropped", "wait-dropped"):
                        if tag[j] == "mech-dropped": ks += kinds(T[j]); dropped += 1; dc += T[j]["cost"]; byd[None] += 0
                        j += 1
                    c = crf_cmd(ks); bycmd[c] += 1; byd[c] += sum(1 for m in range(i + 1, j) if tag[m] == "mech-dropped")
                    calls += 1; i = j
                else: i += 1
        if calls:
            print(f"| {D2NAME[ro]} | {calls} | {dropped} | {(dropped+calls)/calls:.1f} | {dc:.2f} | " + "; ".join(f"{k} {v}/{byd[k]}" for k, v in bycmd.most_common()) + " |")
# per CR (drivers that own one CR), runs 1-5 and pre-run-1
print("\n## Per CR driver: mechanical turns and crf calls (high variant)")
for sc in ("runs 1-5", "pre-run-1 batches"):
    rs = [r for r in rows if r["role"] == "driver" and scope(r) == sc]
    turns = [len(r["turns"]) for r in rs]; mech = []; calls = []; drop = []
    for r in rs:
        keep, capnext, shrink, tag = plan(r, {"waits": "high", "mech": "high"})
        mech.append(sum(1 for i in range(1, len(r["turns"])) if category(r, i).startswith("mechanical")))
        calls.append(sum(1 for x in tag if x == "crf-call")); drop.append(sum(1 for x in tag if x.endswith("dropped")))
    print(f"{sc}: {len(rs)} drivers; turns/CR median {st.median(turns)}, mechanical turns/CR median {st.median(mech)} (mean {st.mean(mech):.1f}); crf calls/CR median {st.median(calls)} (mean {st.mean(calls):.1f}); turns dropped/CR median {st.median(drop)} (mean {st.mean(drop):.1f})")
# category mix of all turns, real cost
print("\n## Turn categories per role (real $)")
for ro in ORCH:
    rs = [r for r in rows if r["role"] == ro]; c = collections.Counter(); n = collections.Counter()
    for r in rs:
        for i, t in enumerate(r["turns"]):
            k = category(r, i); c[k] += t["cost"]; n[k] += 1
    print(f"{D2NAME[ro]}: " + "; ".join(f"{k} {n[k]} ${v:.2f}" for k, v in c.most_common()))
