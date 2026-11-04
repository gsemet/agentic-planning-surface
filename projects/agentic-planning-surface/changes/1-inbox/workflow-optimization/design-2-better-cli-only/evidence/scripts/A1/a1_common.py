"""Shared helpers for A1 (design 2, orchestration roles). Builds on design-1 common.py."""
import sys, os, re, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
MAIN_ID = "dd375646-4450-4e52-a643-89ff1d9e405a"
ORCH = ["orchestrator", "driver", "stack driver", "task driver", "integrator"]
D2NAME = {"orchestrator": "Foreman (orchestrator)", "driver": "Driver (CR)", "stack driver": "Driver: stack",
          "task driver": "Driver: task", "integrator": "Driver: integrator", "main": "Main session dd375646"}
CPT = 2.4  # chars per token, calibrated: median 2.45 on 881 turns with >20k chars of input (a1_anatomy.py, out/a1_calib.txt)

def scope(r):
    if r["run"]: return "runs 1-5"
    if r["ws"] == "CR pipeline before run 1": return "pre-run-1 batches"
    return "other workstreams"

def load_all():
    rows, byid = load()
    for r in rows:
        if r["meta"].get("main"):
            r["is_main"] = r["meta"]["session"] == MAIN_ID
            r["role"] = "main" if r["is_main"] else "main-other"
        else: r["is_main"] = False
    return rows, byid

def pct(a, q):
    a = sorted(a); return a[min(len(a) - 1, int(q * len(a)))] if a else 0

def is_compact(t): return any(x[0] in ("compact", "compact_summary") for x in t["inputs"])

def in_tokens(x):
    """Token estimate of one input item."""
    return x[1] / CPT

def input_class(x):
    k = x[0]
    if k == "tool_result":
        name, short = x[2][0], x[2][1]
        if name in ("Agent", "Task"): return "child return (Agent result)"
        if name == "Read": return status_or_brief(short)
        if name == "Bash":
            b = bash_kind(short)
            if b in ("poll", "sleep"): return "poll/wait output"
            if b in ("git-read", "gh-read", "gh-ci"): return "git/gh status output"
            if b.startswith("git") or b.startswith("gh-"): return "git/gh write output"
            if b == "read-shell":
                return status_or_brief(short)
            if b in ("gate-long", "gate-fast", "okfreq"): return "gate output"
            return "other shell output"
        if name in ("Monitor", "TaskOutput", "BashOutput"): return "poll/wait output"
        if name == "SendMessage": return "send ack"
        return "other tool result"
    if k == "handback": return "hand-back report"
    if k == "task_notif": return "task notification"
    if k == "peer_msg": return "peer message"
    if k == "steer": return "steering message"
    if k in ("compact", "compact_summary"): return "compaction summary"
    return "system/other"

def turn_cost(fam, read, w5, w1h, out, inp=0):
    p = PRICE[fam]; return (inp * p[0] + w5 * p[1] + w1h * p[2] + read * p[3] + out * p[4]) / 1e6

STATUSF = re.compile(r"STATE\.md|ORCHESTRATOR|STACK-STATE|TASKS\.md|\.lock|report|STATUS", re.I)
BRIEFF = re.compile(r"SKILL\.md|references/|00-request|RUN-BRIEF|brief|rules\.md|task\.md|AGENTS\.md|guideline", re.I)
def status_or_brief(short):
    if BRIEFF.search(short): return "brief/skill read"
    if STATUSF.search(short): return "status read"
    return "file read"

def category(r, i):
    """Turn category, copied from design-1 c_lever1.py."""
    t = r["turns"][i]
    if i == 0: return "first turn (brief)"
    ks = [x[0] for x in t["inputs"]]
    if "steer" in ks: return "steer (message from main/user)"
    if "peer_msg" in ks: return "peer message"
    res = [x for x in t["inputs"] if x[0] == "tool_result"]
    exc = any(x[2][2] or set(x[2][5]) & {"conflict", "denied"} for x in res) or any("fail" in x[2][5] and bash_kind(x[2][1]) in ("gate-long", "gate-fast", "gh-ci", "poll") for x in res if x[2][0] == "Bash")
    hb = "handback" in ks; tn = "task_notif" in ks
    kinds = [tool_kind(x) for x in t["tools"]]
    if exc: return "exception (error/conflict/denied/failed gate or CI)"
    if hb and any(k == "spawn" for k in kinds): return "handback -> spawn next"
    if hb: return "handback handling"
    if tn: return "background wait resumed"
    if not kinds: return "text only / report"
    if any(k == "spawn" for k in kinds): return "spawn"
    if any(k == "sendmessage" for k in kinds): return "send message"
    if all(k.startswith("bash:") or k in ("read-status", "edit-status", "wait-tool", "read") for k in kinds):
        if any(k in ("edit-status",) or k == "bash:write-shell" for k in kinds): return "mechanical: status/table write"
        if any(k in ("bash:poll", "bash:sleep", "wait-tool", "bash:gh-ci") for k in kinds): return "mechanical: poll/wait/CI"
        if any(k.startswith("bash:git") or k.startswith("bash:gh") for k in kinds): return "mechanical: git/gh"
        if any(k.startswith("bash:gate") for k in kinds): return "mechanical: gates"
        return "mechanical: reads/other shell"
    return "other (edits src/other tools)"
