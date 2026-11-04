"""3b. Image dimensions in worker tool results (PNG/JPEG headers), estimated tokens, downscale simulation."""
import sys, os, base64, struct, glob; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
paths = {}
for p in glob.glob(os.path.expanduser("~/.claude/projects/*/*/subagents/*.jsonl")):
    paths[os.path.basename(p)[6:-6]] = p
def dims(b64):
    raw = base64.b64decode(b64[:400] + "=" * (-len(b64[:400]) % 4))
    if raw[:8] == b"\x89PNG\r\n\x1a\n": return struct.unpack(">II", raw[16:24])
    if raw[:2] == b"\xff\xd8":
        full = base64.b64decode(b64 + "=" * (-len(b64) % 4)); i = 2
        while i < len(full) - 9:
            if full[i] != 0xFF: i += 1; continue
            m = full[i + 1]
            if m in (0xC0, 0xC1, 0xC2):
                h, w_ = struct.unpack(">HH", full[i + 5:i + 9]); return (w_, h)
            i += 2 + struct.unpack(">H", full[i + 2:i + 4])[0]
    return None
def toks(w, h, maxedge=1568, maxpx=1.15e6):
    s = min(1.0, maxedge / max(w, h)); w2, h2 = w * s, h * s
    if w2 * h2 > maxpx: f = (maxpx / (w2 * h2)) ** 0.5; w2 *= f; h2 *= f
    return w2 * h2 / 750
want = {w["meta"]["agent_id"]: w for w in W if any(tr.get("img") for t in w["turns"] for tr in t["tools"])}
info = {}
for aid in want:
    with open(paths[aid], errors="replace") as f:
        for line in f:
            if '"image"' not in line: continue
            d = json.loads(line)
            for b in (d.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_result" and isinstance(b.get("content"), list):
                    for x in b["content"]:
                        if isinstance(x, dict) and x.get("type") == "image":
                            dd = dims((x.get("source") or {}).get("data") or "")
                            if dd: info.setdefault(b.get("tool_use_id"), []).append(dd)
agg = collections.defaultdict(list); sim = collections.Counter()
for aid, w in want.items():
    rp = result_pos(w); cuts = collections.defaultdict(list)
    for t in w["turns"]:
        for tr in t["tools"]:
            for (a, b) in info.get(tr["id"], []):
                tk = toks(a, b); agg[w["wrole"]].append((a, b, tk))
                if tr["id"] in rp:
                    j, pos = rp[tr["id"]]
                    for lab, me in (("1000px", 1000), ("800px", 800)):
                        cuts[lab].append((j, pos, max(0, tk - toks(a, b, me))))
                    cuts["as counted (1600) vs real"].append((j, pos, 1600 - tk))
    for lab in cuts: sim[(w["wrole"], lab)] += cut_saving(w, cuts[lab])
for wr, v in agg.items():
    print(f"{wr}: images {len(v)}, median {st.median([a for a,b,c in v]):.0f}x{st.median([b for a,b,c in v]):.0f}, est tokens p50 {st.median([c for a,b,c in v]):.0f} mean {st.mean([c for a,b,c in v]):.0f}, share >=1400 tok {sum(c>=1400 for a,b,c in v)/len(v):.0%}")
    print(f"   downscale to <=1000 px long edge saves ${sim[(wr,'1000px')]:.2f}; <=800 px ${sim[(wr,'800px')]:.2f}")
