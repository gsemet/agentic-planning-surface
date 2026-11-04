# Print main-session assistant text and user prompts in [t-before, t+after] minutes around given timestamps.
import json, os, sys, datetime
P = os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a.jsonl')
def T(s): return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
wins = []
for a in sys.argv[1:]:
    t, b, f = a.split(',')
    c = T(t + ':00Z'); wins.append((c - datetime.timedelta(minutes=int(b)), c + datetime.timedelta(minutes=int(f)), t))
seen = set()
for line in open(P):
    if '"text"' not in line: continue
    try: x = json.loads(line)
    except Exception: continue
    ts = x.get('timestamp')
    if not ts: continue
    tt = T(ts)
    w = next((w for w in wins if w[0] <= tt <= w[1]), None)
    if not w: continue
    m = x.get('message') or {}; c = m.get('content')
    txts = [c] if isinstance(c, str) else [z.get('text', '') for z in (c or []) if isinstance(z, dict) and z.get('type') == 'text']
    for t in txts:
        t = t.strip()
        if not t or t[:80] in seen or t.startswith('<system-reminder>') : continue
        seen.add(t[:80])
        print(f"[{w[2]}] {ts[5:19]} {x.get('type')[:4]}: {t[:420].replace(chr(10),' ')}")
