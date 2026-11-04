# Nesting depth from .meta.json (spawnDepth, parentAgentId) for all sessions in the window.
import json, glob, os, collections, sys
ROOT = os.path.expanduser("~/.claude/projects")
EXCL = "c985a2ca-688a-42f5-b17e-bee5b5729ff4"
rows = []
for mf in glob.glob(ROOT + "/*/*/subagents/*.meta.json"):
    if EXCL in mf: continue
    try: m = json.load(open(mf))
    except Exception: continue
    m["_file"] = mf
    m["_sess"] = mf.split("/")[-3]
    m["_id"] = os.path.basename(mf)[len("agent-"):-len(".meta.json")]
    rows.append(m)
print("meta files:", len(rows))
print("keys:", collections.Counter(k for m in rows for k in m).most_common())
by = {m["_id"]: m for m in rows}
dc = collections.Counter((m["_sess"][:8], m.get("spawnDepth")) for m in rows)
for k, v in sorted(dc.items(), key=lambda x: (x[0][0], str(x[0][1]))): print(k, v)
# computed depth by parent chain
def chain(m):
    c = [m]; seen = set()
    while c[-1].get("parentAgentId") and c[-1]["parentAgentId"] in by and c[-1]["_id"] not in seen:
        seen.add(c[-1]["_id"]); c.append(by[c[-1]["parentAgentId"]])
    return c
mx = collections.Counter()
deep = []
for m in rows:
    c = chain(m)
    mx[len(c)] += 1
    if m.get("spawnDepth", 0) and m.get("spawnDepth") >= 3: deep.append((m.get("spawnDepth"), [x.get("description","")[:45] for x in c]))
print("chain length (1 = child of main):", sorted(mx.items()))
print("depth>=3 samples:", len(deep))
for d, c in deep[:40]: print(d, " <- ".join(c))
