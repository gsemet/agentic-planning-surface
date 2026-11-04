# Find short timestamped quotes for capability evidence. usage: quotes.py FILEID 'regex' [max] [role-filter]
import json, re, sys, os
P = os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a')
fid, rx = sys.argv[1], re.compile(sys.argv[2], re.I); mx = int(sys.argv[3]) if len(sys.argv) > 3 else 6
kinds = sys.argv[4] if len(sys.argv) > 4 else 'text,tool,user'
path = P + '.jsonl' if fid == 'MAIN' else P + '/subagents/' + fid + '.jsonl'
n = 0
for line in open(path):
    if not rx.search(line): continue
    try: x = json.loads(line)
    except Exception: continue
    if x.get('timestamp', '') < os.environ.get('START', '2026-10-17'): continue
    m = x.get('message') or {}; c = m.get('content')
    items = []
    if x.get('type') == 'assistant' and isinstance(c, list):
        for z in c:
            if z.get('type') == 'text' and 'text' in kinds: items.append(('TXT', z['text']))
            if z.get('type') == 'tool_use' and 'tool' in kinds: items.append(('TOOL:' + z['name'], json.dumps(z.get('input'))))
    elif x.get('type') == 'user' and 'user' in kinds:
        if isinstance(c, str): items.append(('USER', c))
        elif isinstance(c, list):
            for z in c:
                if z.get('type') == 'text': items.append(('USER', z['text']))
                if z.get('type') == 'tool_result' and 'result' in kinds:
                    cc = z.get('content'); cc = ' '.join(q.get('text', '') for q in cc if isinstance(q, dict)) if isinstance(cc, list) else str(cc)
                    items.append(('RESULT', cc))
    for k, t in items:
        mm = rx.search(t)
        if not mm: continue
        i = mm.start(); s = t[max(0, i - 160): i + 220].replace('\n', ' ')
        print(f"{x['timestamp'][:19]} {k}: …{s}…"); n += 1
        break
    if n >= mx: break
