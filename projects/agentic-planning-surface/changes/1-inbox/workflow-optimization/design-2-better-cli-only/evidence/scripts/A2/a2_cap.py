"""6b. Context cap (autocompact) per role: when ctx exceeds CAP, summarise and restart at 45k; summary costs a
full read + 3k output + 45k write. Simulated on real turns (later turns keep their own growth)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcommon import *
W, rows, byid = wload()
for CAP in (100000, 150000):
    print(f"\nCAP {CAP//1000}k")
    for wr in WROLES:
        base = new = 0.0; summaries = 0
        for w in W:
            if w["wrole"] != wr: continue
            off = 0.0
            for t in w["turns"]:
                p = PRICE[t["fam"]]; c = ctx(t); base += t["cost"]
                if c - off > CAP:
                    summaries += 1
                    new += (c - off) * p[3] / 1e6 + 3000 * p[4] / 1e6 + 45000 * p[1] / 1e6
                    off = c - 45000
                if c < off: off = 0.0  # natural compaction/restart
                red = min(off, t["cr"])
                new += t["cost"] - red * p[3] / 1e6
        print(f"  {wr:16s} today ${base:7.1f} capped ${new:7.1f} saving ${base-new:6.1f} ({100*(base-new)/base:4.1f}%) summaries {summaries}")
