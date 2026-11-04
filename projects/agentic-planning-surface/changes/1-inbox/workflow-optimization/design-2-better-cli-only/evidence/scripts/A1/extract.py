"""Per-turn extraction of every Claude Code agent active 2026-10-17..27 (UTC timestamps).
Adapted from the Studio cost-analysis analyze.py (same dedupe and pricing rules).
Output: one JSON line per agent with per-turn rows."""
import json, os, re, sys, glob, datetime

ROOT = os.path.expanduser("~/.claude/projects")
START, END = "2026-10-17T00:00:00", "2026-10-28T00:00:00"
EXCLUDE = "c985a2ca-688a-42f5-b17e-bee5b5729ff4"
OUT = sys.argv[1]
PRICE = {"opus": (4.0, 5.0, 8.0, 0.20, 20.0), "sonnet": (2.0, 2.5, 4.0, 0.20, 10.0),
         "haiku": (0.10, 0.125, 0.20, 0.01, 0.50), "fable": (10.0, 12.5, 20.0, 0.25, 50.0)}

def family(model):
    m = (model or "").lower()
    for f in PRICE:
        if f in m:
            return f
    return None

def size_of(cc):
    if cc is None: return 0, 0
    if isinstance(cc, str): return len(cc), 0
    n, img = 0, 0
    for x in cc:
        if isinstance(x, dict) and x.get("type") == "image": img += 1
        elif isinstance(x, dict): n += len(x.get("text") or "")
        else: n += len(str(x))
    return n, img

FL = [("conflict", re.compile(r"CONFLICT|merge conflict|could not apply")),
      ("fail", re.compile(r"\bFAIL(ED)?\b|\bfailed\b|failing|Error:|error TS\d|\u2717|exit code [1-9]|AssertionError|not ok ")),
      ("denied", re.compile(r"[Pp]ermission denied|denied by|was denied|not permitted|auto mode classifier|blocked by policy"))]

def flags(cc):
    if cc is None: return []
    s = cc if isinstance(cc, str) else " ".join((x.get("text") or "") for x in cc if isinstance(x, dict))
    return [k for k, rx in FL if rx.search(s)]

def trig_kind(p):
    if not isinstance(p, str): p = json.dumps(p)
    s = p.lstrip()
    if s.startswith("<agent-message"):
        return "handback" if "[Subagent hand-back]" in s[:200] else "peer_msg"
    if s.startswith("<task-notification"): return "task_notif"
    if s.startswith("<system-reminder") or s.startswith("<local-command") or s.startswith("<command-"): return "system"
    return "steer"

def scan(path, meta):
    turns = {}; order = []
    tool_meta = {}  # tool_use_id -> (name, short)
    pending = []  # inputs accumulated since last assistant line
    last_assist_mid = None
    compactions = 0; in_window = False
    first_prompt = None
    with open(path, errors="replace") as f:
        for line in f:
            if '"type":"api-request' in line[:200] or '"type": "api-request' in line[:200]:
                continue
            try: d = json.loads(line)
            except Exception: continue
            t = d.get("type"); ts = d.get("timestamp") or ""
            if t in ("api-request", "api-request-blob", "api-request-shape"): continue
            if t == "system" and d.get("subtype") == "compact_boundary":
                if START <= ts < END: compactions += 1
                pending.append(("compact", 0, None, ts)); continue
            m = d.get("message") or {}
            if t == "attachment":
                a = d.get("attachment") or {}
                if a.get("type") == "queued_command":
                    p = a.get("prompt") or ""
                    k = trig_kind(p)
                    pending.append((k, len(p) if isinstance(p, str) else len(json.dumps(p)), (p if isinstance(p, str) else json.dumps(p))[:300], ts))
                continue
            if t == "user":
                c = m.get("content")
                if d.get("isCompactSummary"):
                    pending.append(("compact_summary", len(json.dumps(c)), None, ts)); continue
                if isinstance(c, str):
                    if first_prompt is None: first_prompt = c[:400]
                    if d.get("isMeta"): pending.append(("system", len(c), None, ts))
                    else: pending.append((trig_kind(c), len(c), c[:300], ts))
                elif isinstance(c, list):
                    for b in c:
                        if not isinstance(b, dict): continue
                        if b.get("type") == "tool_result":
                            n, img = size_of(b.get("content"))
                            name, short = tool_meta.get(b.get("tool_use_id"), ("?", ""))
                            pending.append(("tool_result", n + img * 1600 * 3.2, [name, short, bool(b.get("is_error")), img, b.get("tool_use_id"), flags(b.get("content"))], ts))
                        elif b.get("type") == "text":
                            txt = b.get("text") or ""
                            if first_prompt is None: first_prompt = txt[:400]
                            pending.append((trig_kind(txt) if not d.get("isMeta") else "system", len(txt), txt[:300], ts))
                continue
            if t == "assistant":
                mid = m.get("id") or d.get("uuid")
                if mid not in turns:
                    turns[mid] = {"ts": ts, "ts_last": ts, "model": m.get("model"), "u": {}, "tools": [],
                                  "inputs": pending, "text": 0}
                    order.append(mid); pending = []
                rec = turns[mid]; rec["ts_last"] = ts
                u = m.get("usage") or {}
                for k in ("input_tokens", "cache_read_input_tokens", "output_tokens"):
                    rec["u"][k] = max(rec["u"].get(k, 0), u.get(k) or 0)
                cc = u.get("cache_creation") or {}
                rec["u"]["w5"] = max(rec["u"].get("w5", 0), cc.get("ephemeral_5m_input_tokens") or 0)
                rec["u"]["w1h"] = max(rec["u"].get("w1h", 0), cc.get("ephemeral_1h_input_tokens") or 0)
                if not cc:
                    rec["u"]["w5"] = max(rec["u"].get("w5", 0), u.get("cache_creation_input_tokens") or 0)
                for c in m.get("content") or []:
                    if c.get("type") == "tool_use":
                        inp = c.get("input") or {}
                        name = c.get("name")
                        if name == "Bash": short = inp.get("command", "")[:300]; bg = bool(inp.get("run_in_background"))
                        elif name in ("Read", "Edit", "Write"): short = inp.get("file_path", ""); bg = False
                        elif name in ("Agent", "Task"): short = (inp.get("description") or "")[:120] + (" [bg]" if inp.get("run_in_background") else ""); bg = bool(inp.get("run_in_background"))
                        elif name == "SendMessage": short = json.dumps(inp)[:200]; bg = False
                        else: short = json.dumps(inp)[:150]; bg = False
                        tool_meta[c.get("id")] = (name, short)
                        rec["tools"].append([name, short, bg, c.get("id")])
                    elif c.get("type") == "text":
                        rec["text"] += len(c.get("text") or "")
    rows = []
    for mid in order:
        r = turns[mid]
        if not (START <= r["ts"] < END): continue
        fam = family(r["model"])
        if r["model"] == "<synthetic>" or fam is None: continue
        in_window = True
        u = r["u"]; p = PRICE[fam]
        cost = (u.get("input_tokens", 0) * p[0] + u.get("w5", 0) * p[1] + u.get("w1h", 0) * p[2]
                + u.get("cache_read_input_tokens", 0) * p[3] + u.get("output_tokens", 0) * p[4]) / 1e6
        rows.append({"ts": r["ts"], "ts_last": r["ts_last"], "fam": fam, "in": u.get("input_tokens", 0),
                     "cr": u.get("cache_read_input_tokens", 0), "w5": u.get("w5", 0), "w1h": u.get("w1h", 0),
                     "out": u.get("output_tokens", 0), "cost": cost, "tools": r["tools"], "inputs": r["inputs"], "text": r["text"]})
    if not in_window: return None
    return {"file": path, "meta": meta, "turns": rows, "compactions": compactions, "first_prompt": first_prompt}

n = 0; tot = 0.0
with open(OUT, "w") as out:
    for path in glob.glob(os.path.join(ROOT, "**", "*.jsonl"), recursive=True):
        if EXCLUDE in path: continue
        if os.path.getmtime(path) < datetime.datetime(2026, 10, 16).timestamp(): continue
        mp = path[:-6] + ".meta.json"
        meta = json.load(open(mp)) if os.path.exists(mp) else {"main": True}
        parts = path.split(os.sep)
        meta["project"] = next((p for p in parts if p.startswith("-Users")), "?")
        meta["session"] = next((p for p in parts if re.fullmatch(r"[0-9a-f-]{36}(\.jsonl)?", p)), "?").replace(".jsonl", "")
        meta["agent_id"] = os.path.basename(path)[:-6].replace("agent-", "")
        r = scan(path, meta)
        if r:
            out.write(json.dumps(r) + "\n"); n += 1; tot += sum(t["cost"] for t in r["turns"])
print(n, "agents", round(tot, 2), "USD")
