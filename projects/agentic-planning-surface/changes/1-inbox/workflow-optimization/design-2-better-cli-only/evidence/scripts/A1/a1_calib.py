"""Chars-per-token calibration: context growth vs characters of new input, on turns with large inputs."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a1_common import *
rows, byid = load_all()
for lo in (5000, 20000, 50000):
    rs = []
    for r in rows:
        T = r["turns"]
        for i in range(1, len(T)):
            t, p = T[i], T[i - 1]
            if is_compact(t) or any(x[0] == "tool_result" and x[2][3] for x in t["inputs"]): continue
            ch = sum(x[1] for x in t["inputs"]); d = ctx(t) - ctx(p) - p["out"]
            if ch > lo and d > 0: rs.append(ch / d)
    print(f"turns with > {lo} chars of new input: n={len(rs)}, median chars/token {st.median(rs):.2f}")
