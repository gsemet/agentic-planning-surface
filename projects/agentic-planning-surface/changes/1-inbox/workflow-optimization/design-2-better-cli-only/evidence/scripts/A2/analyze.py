"""Token and cost profile of every Claude Code session and sub-agent active in a date window.

Reads ~/.claude/projects/**.jsonl, dedupes assistant messages by message id, and writes
agents.json (one row per agent) for later aggregation.
"""
import json, os, re, sys, glob, collections, datetime

ROOT = os.path.expanduser("~/.claude/projects")
START = "2026-10-19T00:00:00"
END = "2026-10-27T00:00:00"
OUT = sys.argv[1]

# $/MTok: input, 5m write, 1h write, cache read, output
PRICE = {
    "opus": (4.0, 5.0, 8.0, 0.20, 20.0),
    "sonnet": (2.0, 2.5, 4.0, 0.20, 10.0),
    "haiku": (0.10, 0.125, 0.20, 0.01, 0.50),
    "fable": (10.0, 12.5, 20.0, 0.25, 50.0),
}


def family(model):
    m = (model or "").lower()
    for f in PRICE:
        if f in m:
            return f
    return None


def bash_kind(cmd):
    c = cmd.strip()
    c = re.sub(r"^(cd [^&;]+(&&|;)\s*)+", "", c)
    c = re.sub(r"^(env (-u \S+ )*|[A-Z_]+=\S+ )+", "", c)
    if re.search(r"\bsleep\b", c) and re.search(r"\b(gh run|gh pr checks|until|while)\b", c):
        return "poll"
    for pat, kind in [
        (r"^(rtk )?git ", "git"), (r"^gh (run|pr checks|workflow)", "gh-ci"), (r"^gh stack", "gh-stack"),
        (r"^gh ", "gh-other"), (r"^just (check|preflight|ci-|test)", "just-gates"), (r"^just ", "just-other"),
        (r"okfreq", "okfreq"), (r"^(npm|npx|node|fnm)", "node"), (r"^(uv|python3?|pytest)", "python"),
        (r"^(cat|head|tail|sed -n|grep|rg|ls|find|wc|awk)", "read-shell"), (r"^sleep", "sleep"),
    ]:
        if re.search(pat, c):
            return kind
    return "other"


def scan(path, meta):
    msgs = {}  # message id -> record
    tools = collections.Counter()
    bash = collections.Counter()
    result_chars = collections.Counter()
    tool_name_by_id = {}
    bash_kind_by_id = {}
    read_kind_by_id = {}
    results = []
    first_user = None
    ts_min, ts_max = None, None
    reads = collections.Counter()
    in_window = False
    with open(path, errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            ts = d.get("timestamp")
            if ts:
                if START <= ts < END:
                    in_window = True
                    ts_min = ts if not ts_min or ts < ts_min else ts_min
                    ts_max = ts if not ts_max or ts > ts_max else ts_max
                elif d.get("type") == "assistant":
                    continue  # outside the window
            t = d.get("type")
            m = d.get("message") or {}
            if t == "user":
                content = m.get("content")
                if first_user is None and isinstance(content, str):
                    first_user = content
                if isinstance(content, list):
                    for c in content:
                        if c.get("type") == "tool_result":
                            name = tool_name_by_id.get(c.get("tool_use_id"), "?")
                            cc = c.get("content")
                            size = len(cc) if isinstance(cc, str) else len(json.dumps(cc)) if cc else 0
                            result_chars[name] += size
                            kind = name
                            if name == "Bash":
                                kind = "Bash:" + bash_kind_by_id.get(c.get("tool_use_id"), "?")
                            if name == "Read":
                                kind = "Read:" + read_kind_by_id.get(c.get("tool_use_id"), "?")
                            if isinstance(cc, list) and any(isinstance(x, dict) and x.get("type") == "image" for x in cc):
                                kind += ":image"
                                size = 1600 * 3.2 * sum(1 for x in cc if isinstance(x, dict) and x.get("type") == "image")
                            results.append([len(msgs), kind, size])
                        elif c.get("type") == "text" and first_user is None:
                            first_user = c.get("text", "")
            elif t == "assistant" and ts and START <= ts < END:
                mid = m.get("id") or d.get("uuid")
                u = m.get("usage") or {}
                rec = msgs.setdefault(mid, {"model": m.get("model"), "u": {}, "ts": ts, "seq": len(msgs)})
                for k in ("input_tokens", "cache_read_input_tokens", "output_tokens"):
                    rec["u"][k] = max(rec["u"].get(k, 0), u.get(k) or 0)
                cc = u.get("cache_creation") or {}
                rec["u"]["w5"] = max(rec["u"].get("w5", 0), cc.get("ephemeral_5m_input_tokens") or 0)
                rec["u"]["w1h"] = max(rec["u"].get("w1h", 0), cc.get("ephemeral_1h_input_tokens") or 0)
                if not cc:
                    rec["u"]["w5"] = max(rec["u"].get("w5", 0), u.get("cache_creation_input_tokens") or 0)
                for c in m.get("content") or []:
                    if c.get("type") == "tool_use":
                        name = c.get("name")
                        tool_name_by_id[c.get("id")] = name
                        tools[name] += 1
                        inp = c.get("input") or {}
                        if name == "Bash":
                            bash[bash_kind(inp.get("command", ""))] += 1
                            bash_kind_by_id[c.get("id")] = bash_kind(inp.get("command", ""))
                        if name == "Read":
                            fp = inp.get("file_path", "")
                            read_kind_by_id[c.get("id")] = "rules" if re.search(r"constitution|guidelines|AGENTS\.md|CLAUDE\.md|SKILL\.md", fp) else "test" if "/test" in fp else "requirements" if "/requirements/" in fp else ".agents" if "/.agents/" in fp else "src" if "/src/" in fp else "other"
                        if name == "Read":
                            p = inp.get("file_path", "")
                            if re.search(r"constitution|guidelines|AGENTS\.md|CLAUDE\.md", p):
                                reads["rules"] += 1
                            reads["all"] += 1
    if not in_window or not msgs:
        return None
    tot = collections.Counter()
    cost = 0.0
    models = collections.Counter()
    max_ctx = 0
    for rec in msgs.values():
        u = rec["u"]
        fam = family(rec["model"])
        if rec["model"] == "<synthetic>" or fam is None:
            continue
        models[fam] += 1
        for k, v in u.items():
            tot[k] += v
        p = PRICE[fam]
        cost += (u.get("input_tokens", 0) * p[0] + u.get("w5", 0) * p[1] + u.get("w1h", 0) * p[2]
                 + u.get("cache_read_input_tokens", 0) * p[3] + u.get("output_tokens", 0) * p[4]) / 1e6
        ctx = u.get("input_tokens", 0) + u.get("w5", 0) + u.get("w1h", 0) + u.get("cache_read_input_tokens", 0)
        max_ctx = max(max_ctx, ctx)
    seq = []
    for rec in sorted(msgs.values(), key=lambda r: r["seq"]):
        u = rec["u"]
        if family(rec["model"]) is None:
            continue
        seq.append([u.get("input_tokens", 0) + u.get("w5", 0) + u.get("w1h", 0) + u.get("cache_read_input_tokens", 0),
                    u.get("w5", 0) + u.get("w1h", 0), u.get("output_tokens", 0), rec["ts"], family(rec["model"])])
    return {
        "seq": seq, "results": results,
        "file": path, "meta": meta, "turns": len(msgs), "tokens": dict(tot), "cost": cost,
        "models": dict(models), "tools": dict(tools), "bash": dict(bash), "result_chars": dict(result_chars),
        "reads": dict(reads), "prompt_chars": len(first_user or ""), "prompt_head": (first_user or "")[:300],
        "ts_min": ts_min, "ts_max": ts_max, "max_ctx": max_ctx,
    }


rows = []
for path in glob.glob(os.path.join(ROOT, "**", "*.jsonl"), recursive=True):
    if os.path.getmtime(path) < datetime.datetime(2026, 10, 19).timestamp():
        continue
    meta_path = path[:-6] + ".meta.json"
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {"main": True}
    parts = path.split(os.sep)
    meta["project"] = next((p for p in parts if p.startswith("-Users")), "?")
    meta["session"] = next((p for p in parts if re.fullmatch(r"[0-9a-f-]{36}(\.jsonl)?", p)), "?").replace(".jsonl", "")
    meta["agent_id"] = os.path.basename(path)[:-6]
    r = scan(path, meta)
    if r:
        rows.append(r)
json.dump(rows, open(OUT, "w"))
print(len(rows), "agents;", round(sum(r["cost"] for r in rows), 2), "USD")
