# Did depth-3 agents try to spawn subagents (Agent/Task tool) and what happened?
import json, glob, os, collections
ROOT = os.path.expanduser("~/.claude/projects")
res = collections.Counter(); samples = []
tools3 = collections.Counter()
for mf in glob.glob(ROOT + "/*/*/subagents/*.meta.json"):
    if "c985a2ca" in mf: continue
    m = json.load(open(mf))
    if m.get("spawnDepth") != 3: continue
    jf = mf[:-len(".meta.json")] + ".jsonl"
    if not os.path.exists(jf): continue
    pend = {}
    for l in open(jf):
        try: r = json.loads(l)
        except Exception: continue
        msg = r.get("message") or {}
        c = msg.get("content")
        if not isinstance(c, list): continue
        for b in c:
            if b.get("type") == "tool_use":
                tools3[b["name"]] += 1
                if b["name"] in ("Agent", "Task"):
                    pend[b["id"]] = (r.get("timestamp"), b["input"].get("description"), b["input"].get("subagent_type"))
            if b.get("type") == "tool_result" and b.get("tool_use_id") in pend:
                txt = b.get("content")
                if isinstance(txt, list): txt = " ".join(x.get("text", "") for x in txt if isinstance(x, dict))
                ok = "err" if b.get("is_error") else "ok"
                res[ok] += 1
                samples.append((ok, m.get("description"), pend[b["tool_use_id"]], str(txt)[:300].replace("\n", " ")))
print("depth-3 tool use counts:", tools3.most_common(30))
print("Agent calls from depth-3:", res)
for s in samples[:30]: print(s)
