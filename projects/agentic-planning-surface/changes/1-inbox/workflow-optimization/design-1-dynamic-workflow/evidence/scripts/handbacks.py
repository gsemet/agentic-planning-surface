import json, re, sys, os
base = os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a/subagents/')
rows = [r for r in json.load(open('agents.json')) if r['first'] and r['last'] >= '2026-10-17']
pat = re.compile(sys.argv[1], re.I)
out = open(sys.argv[2], 'w')
for r in sorted(rows, key=lambda r: r['first']):
    if not pat.search(r['desc']): continue
    msgs = []; prompt = None
    for line in open(base + r['id'] + '.jsonl'):
        d = json.loads(line)
        if d.get('type') == 'user' and prompt is None and isinstance(d['message']['content'], str):
            prompt = d['message']['content']
        if d.get('type') != 'assistant': continue
        for b in d['message'].get('content', []):
            if b.get('type') == 'tool_use' and b['name'] == 'SubagentHandback':
                msgs.append((d['timestamp'][:16], b['input'].get('message', '')))
    out.write(f"\n===== {r['first'][:16]} {r['id']} d{r['depth']} parent={r['parent']} {r['model']} :: {r['desc']}\n")
    if not msgs:
        out.write(f"(no handback; last ts {r['last'][:16]}, nasst {r['nasst']})\n")
    for ts, m in msgs:
        out.write(f"[{ts}] {m}\n")
print('ok')
