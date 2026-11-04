import sys, os, json, re, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
HERE = os.path.dirname(os.path.abspath(__file__))
WDATA = os.path.join(HERE, "..", "..", "data", "A2", "workers.jsonl")
WROLES = ["coder", "writer (req)", "inspector", "critic (req)", "analyst (req)", "analyst (other)", "conflict fixer"]
CF = re.compile(r"rebase conflict|resolve rebase|conflict resolution|rebased cr|review rebased|rebase fix", re.I)
def wrole(r):
    if r["role"] in ("coder/writer", "reviewer") and CF.search(r["desc"]): return "conflict fixer"
    req = r["ws"].startswith("requirements base")
    if r["role"] == "coder/writer": return "writer (req)" if req else "coder"
    if r["role"] == "reviewer": return "critic (req)" if req else "inspector"
    if r["role"] == "analyst": return "analyst (req)" if req else "analyst (other)"
    return None
FACT = lambda r: r["run"] is not None or r["ws"] == "CR pipeline before run 1"
def wload():
    rows, byid = load()
    W = []
    for l in open(WDATA):
        w = json.loads(l); a = byid.get(w["meta"]["agent_id"])
        if not a: continue
        wr = wrole(a)
        if not wr: continue
        w["role"] = a["role"]; w["wrole"] = wr; w["ws"] = a["ws"]; w["run"] = a["run"]; w["desc"] = a["desc"]
        w["fact"] = FACT(a); w["ancestors"] = a["ancestors"]
        for t in w["turns"]:
            p = PRICE[t["fam"]]
            t["cost"] = (t["in"] * p[0] + t["w5"] * p[1] + t["w1h"] * p[2] + t["cr"] * p[3] + t["out"] * p[4]) / 1e6
        w["cost"] = sum(t["cost"] for t in w["turns"])
        W.append(w)
    return W, rows, byid
def pct(v, q):
    v = sorted(v); return v[min(len(v) - 1, int(q * (len(v) - 1)))] if v else 0
def tcost(t, fam=None, ttl="5m"):
    p = PRICE[fam or t["fam"]]
    w = t["w5"] + t["w1h"]
    return (t["in"] * p[0] + w * (p[1] if ttl == "5m" else p[2]) + t["cr"] * p[3] + t["out"] * p[4]) / 1e6

CPT = 3.81  # chars per token, calibrated on 777 first turns (a2_payload.py)
def cut_saving(w, cuts, fam=None):
    """cuts: list of (turn_index, pos_tokens, tokens): from turn_index on, `tokens` at context position
    `pos_tokens` disappear. Billed per later turn at read price where the position < cache read,
    else write price (5-min). Carry stops when the context shrinks below the position (compaction)."""
    T = w["turns"]; s = 0.0
    for (i0, pos, tok) in cuts:
        if tok <= 0: continue
        for j in range(i0, len(T)):
            t = T[j]; p = PRICE[fam or t["fam"]]
            if j > i0 and ctx(t) < pos + tok * 0.5: break
            rd = max(0.0, min(pos + tok, t["cr"]) - pos)
            wr = max(0.0, min(pos + tok, t["cr"] + t["w5"] + t["w1h"]) - max(pos, t["cr"]))
            s += (rd * p[3] + wr * p[1]) / 1e6
    return s
def result_pos(w):
    """map tool_use id -> (turn index where its result first appears, context position before it)."""
    T = w["turns"]; m = {}
    for j, t in enumerate(T):
        prev = ctx(T[j - 1]) + T[j - 1]["out"] if j else 0
        for x in t["inputs"]:
            if x[0] == "tool_result" and len(x) > 3: m[x[3]] = (j, prev)
    return m
