# Peak number of live subagents (first..last transcript timestamp) in the main session, by depth.
import json, glob, os, collections
P = os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a/subagents')
iv = []
for mf in glob.glob(P + '/*.meta.json'):
    m = json.load(open(mf)); jf = mf[:-10] + '.jsonl'
    first = last = None
    with open(jf, 'rb') as fh:
        for line in fh:
            if b'"timestamp"' in line:
                try: first = json.loads(line)['timestamp']; break
                except Exception: pass
        fh.seek(0, 2); size = fh.tell(); fh.seek(max(0, size - 200000))
        for line in fh.read().splitlines():
            if b'"timestamp"' in line:
                try: last = json.loads(line)['timestamp']
                except Exception: pass
    if first and last and last >= '2026-10-22': iv.append((first, last, m.get('spawnDepth'), m.get('description', '')))
ev = sorted([(a, 1, d) for a, b, d, _ in iv] + [(b, -1, d) for a, b, d, _ in iv])
cur = collections.Counter(); peak = (0, None, None)
for t, k, d in ev:
    cur[d] += k; tot = sum(cur.values())
    if tot > peak[0]: peak = (tot, t, dict(cur))
print('peak live subagents', peak)
# hours with >=15 live
for lo, hi, lab in [('2026-10-22T16', '2026-10-24', 'runs 10-22/23'), ('2026-10-25T16', '2026-10-26T07', 'P1+P2 stack'), ('2026-10-26T18', '2026-10-27T07', 'P1 stack night'), ('2026-10-27T10', '2026-10-27T16', 'runs 2-3'), ('2026-10-27T16', '2026-10-28', 'runs 4-5')]:
    cur = collections.Counter(); pk = (0, None, None)
    for t, k, d in ev:
        cur[d] += k
        if lo <= t < hi and sum(cur.values()) > pk[0]: pk = (sum(cur.values()), t[5:16], dict(cur))
    print(lab, 'peak', pk)
