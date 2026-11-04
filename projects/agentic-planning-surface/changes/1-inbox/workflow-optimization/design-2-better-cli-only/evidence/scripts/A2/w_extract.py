"""A2 worker extraction: per subagent, per turn usage + detailed tool calls/results + start payload.
Same dedupe/pricing/window as design-1 extract.py; adds instruction payload, tool-schema size,
full commands, Read ranges, result sizes, image bytes, call wall time, skill loads."""
import json, os, re, sys, glob, datetime
ROOT = os.path.expanduser("~/.claude/projects")
START, END = "2026-10-17T00:00:00", os.environ.get("A2END", "2026-10-27T21:48:30")
EXCLUDE = "c985a2ca-688a-42f5-b17e-bee5b5729ff4"
OUT = sys.argv[1]
def family(m):
    m = (m or "").lower()
    for f in ("opus", "sonnet", "haiku", "fable"):
        if f in m: return f
    return None
def csize(cc):
    if cc is None: return 0, 0, 0
    if isinstance(cc, str): return len(cc), 0, 0
    n = img = b64 = 0
    for x in cc:
        if isinstance(x, dict) and x.get("type") == "image":
            img += 1; b64 += len(((x.get("source") or {}).get("data")) or "")
        elif isinstance(x, dict): n += len(x.get("text") or "")
        else: n += len(str(x))
    return n, img, b64
def ctext(cc):
    if cc is None: return ""
    if isinstance(cc, str): return cc
    return " ".join((x.get("text") or "") for x in cc if isinstance(x, dict))
def scan(path, meta):
    turns = {}; order = []; tools = {}; pending = []
    start = {"att": {}, "instr": [], "sys": 0, "tools": 0, "toolsizes": {}, "brief": 0, "brief_text": ""}
    seen_assist = False; skills = []; last_skill = None; meta_after = []
    with open(path, errors="replace") as f:
        for line in f:
            try: d = json.loads(line)
            except Exception: continue
            t = d.get("type"); ts = d.get("timestamp") or ""
            if t in ("api-request", "api-request-blob", "api-request-shape"): continue
            if t == "system" and d.get("subtype") == "compact_boundary":
                pending.append(("compact", 0, ts)); continue
            m = d.get("message") or {}
            if t == "attachment":
                a = d.get("attachment") or {}; at = a.get("type")
                if at == "prompt_snapshot" and a.get("tools") and not start["tools"]:
                    start["sys"] = sum(len(x) for x in a.get("systemPrompt") or [])
                    start["tools"] = len(json.dumps(a["tools"]))
                    start["toolsizes"] = {x.get("name"): len(json.dumps(x)) for x in a["tools"] if isinstance(x, dict)}
                    continue
                if at == "prompt_snapshot": continue
                if not seen_assist:
                    start["att"][at] = start["att"].get(at, 0) + len(json.dumps(a))
                    if at == "instructions":
                        for fi in a.get("files") or []: start["instr"].append((fi.get("path"), fi.get("type"), len(fi.get("content") or "")))
                if at == "queued_command":
                    p = a.get("prompt") or ""; pending.append(("queued", len(p) if isinstance(p, str) else len(json.dumps(p)), ts))
                continue
            if t == "user":
                c = m.get("content")
                if d.get("isCompactSummary"): pending.append(("compact_summary", len(json.dumps(c)), ts)); continue
                if isinstance(c, str):
                    if not seen_assist and not d.get("isMeta") and not start["brief"]:
                        start["brief"] = len(c); start["brief_text"] = c[:6000]
                    if d.get("isMeta") and last_skill is not None: skills[last_skill][2] += len(c)
                    pending.append(("meta" if d.get("isMeta") else "user", len(c), ts))
                elif isinstance(c, list):
                    for b in c:
                        if not isinstance(b, dict): continue
                        if b.get("type") == "tool_result":
                            n, img, b64 = csize(b.get("content")); tid = b.get("tool_use_id")
                            if tid in tools:
                                tr = tools[tid]; tr["rc"] = n; tr["img"] = img; tr["b64"] = b64; tr["rts"] = ts; tr["err"] = bool(b.get("is_error"))
                                tx = ctext(b.get("content")); tr["head"] = tx[:160]; tr["tail"] = tx[-200:]
                            pending.append(("tool_result", n + img * 1600 * 3.2, ts, tid))
                        elif b.get("type") == "text":
                            txt = b.get("text") or ""
                            if not seen_assist and not d.get("isMeta") and not start["brief"]:
                                start["brief"] = len(txt); start["brief_text"] = txt[:6000]
                            if d.get("isMeta") and last_skill is not None: skills[last_skill][2] += len(txt)
                            pending.append(("meta" if d.get("isMeta") else "user", len(txt), ts))
                continue
            if t == "assistant":
                seen_assist = True
                mid = m.get("id") or d.get("uuid")
                if mid not in turns:
                    turns[mid] = {"ts": ts, "ts_last": ts, "model": m.get("model"), "u": {}, "tools": [], "inputs": pending, "text": 0, "think": 0, "tin": 0}
                    order.append(mid); pending = []
                rec = turns[mid]; rec["ts_last"] = ts
                u = m.get("usage") or {}
                for k in ("input_tokens", "cache_read_input_tokens", "output_tokens"):
                    rec["u"][k] = max(rec["u"].get(k, 0), u.get(k) or 0)
                cc = u.get("cache_creation") or {}
                rec["u"]["w5"] = max(rec["u"].get("w5", 0), cc.get("ephemeral_5m_input_tokens") or 0)
                rec["u"]["w1h"] = max(rec["u"].get("w1h", 0), cc.get("ephemeral_1h_input_tokens") or 0)
                if not cc: rec["u"]["w5"] = max(rec["u"].get("w5", 0), u.get("cache_creation_input_tokens") or 0)
                for c in m.get("content") or []:
                    ty = c.get("type")
                    if ty == "tool_use":
                        inp = c.get("input") or {}; name = c.get("name")
                        rec["tin"] += len(json.dumps(inp))
                        tr = {"id": c.get("id"), "name": name, "ts": ts, "rc": None, "img": 0, "b64": 0, "rts": None, "err": False}
                        if name == "Bash": tr["cmd"] = (inp.get("command") or "")[:3000]; tr["bg"] = bool(inp.get("run_in_background")); tr["timeout"] = inp.get("timeout")
                        elif name in ("Read", "Edit", "Write", "NotebookEdit"):
                            tr["path"] = inp.get("file_path", ""); tr["off"] = inp.get("offset"); tr["lim"] = inp.get("limit")
                            if name == "Write": tr["wlen"] = len(inp.get("content") or "")
                            if name == "Edit": tr["wlen"] = len(inp.get("new_string") or "") + len(inp.get("old_string") or "")
                        elif name == "Skill": tr["skill"] = inp.get("skill"); skills.append([inp.get("skill"), ts, 0]); last_skill = len(skills) - 1
                        elif name in ("Grep", "Glob"): tr["pat"] = json.dumps(inp)[:300]
                        elif name in ("Agent", "Task"): tr["desc"] = inp.get("description"); tr["bg"] = bool(inp.get("run_in_background"))
                        elif name == "SubagentHandback": tr["hb"] = len(inp.get("message") or "")
                        else: tr["inp"] = json.dumps(inp)[:200]
                        tools[c.get("id")] = tr; rec["tools"].append(c.get("id"))
                    elif ty == "text": rec["text"] += len(c.get("text") or "")
                    elif ty == "thinking": rec["think"] += 1
                if name_last := None: pass
    rows = []
    for mid in order:
        r = turns[mid]
        if not (START <= r["ts"] < END): continue
        fam = family(r["model"])
        if r["model"] == "<synthetic>" or fam is None: continue
        u = r["u"]
        rows.append({"ts": r["ts"], "ts_last": r["ts_last"], "fam": fam, "in": u.get("input_tokens", 0), "cr": u.get("cache_read_input_tokens", 0),
                     "w5": u.get("w5", 0), "w1h": u.get("w1h", 0), "out": u.get("output_tokens", 0), "text": r["text"], "think": r["think"], "tin": r["tin"],
                     "tools": [tools[i] for i in r["tools"]], "inputs": r["inputs"]})
    if not rows: return None
    return {"meta": meta, "start": start, "skills": skills, "turns": rows}
n = 0
with open(OUT, "w") as out:
    for path in glob.glob(os.path.join(ROOT, "*", "*", "subagents", "*.jsonl")):
        if EXCLUDE in path: continue
        if os.path.getmtime(path) < datetime.datetime(2026, 10, 16).timestamp(): continue
        mp = path[:-6] + ".meta.json"
        meta = json.load(open(mp)) if os.path.exists(mp) else {}
        parts = path.split(os.sep)
        meta["project"] = next((p for p in parts if p.startswith("-Users")), "?")
        meta["session"] = parts[-3]
        meta["agent_id"] = os.path.basename(path)[:-6].replace("agent-", "")
        r = scan(path, meta)
        if r: out.write(json.dumps(r) + "\n"); n += 1
print(n, "subagents")
