"""Size of Agent/SendMessage prompts written by orchestration roles and the main session (output tokens spent on spawning boilerplate)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_common import *
import json
rows, byid = load_all()
res = collections.defaultdict(list); sm = collections.defaultdict(list)
for r in rows:
    if r["role"] not in ORCH + ["main"]: continue
    with open(r["file"], errors="replace") as f:
        for line in f:
            if '"tool_use"' not in line: continue
            try: d = json.loads(line)
            except Exception: continue
            if d.get("type") != "assistant": continue
            if not ("2026-10-17" <= (d.get("timestamp") or "") < "2026-10-28"): continue
            for c in (d.get("message") or {}).get("content") or []:
                if c.get("type") == "tool_use" and c.get("name") in ("Agent", "Task"):
                    res[r["role"]].append(len((c.get("input") or {}).get("prompt") or ""))
                if c.get("type") == "tool_use" and c.get("name") == "SendMessage":
                    sm[r["role"]].append(len(json.dumps(c.get("input") or {})))
for k, v in res.items():
    print(f"{k}: Agent prompts n={len(v)} median {st.median(v)/CPT:.0f} tok, p90 {pct(v,.9)/CPT:.0f}, total {sum(v)/CPT/1e3:.0f}k tok")
for k, v in sm.items():
    print(f"{k}: SendMessage n={len(v)} median {st.median(v)/CPT:.0f} tok, total {sum(v)/CPT/1e3:.0f}k tok")
