import json,sys,re
f='/Users/az02065/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a/subagents/agent-%s.jsonl'%sys.argv[1]
pat=re.compile(sys.argv[2],re.I); seen=set()
for line in open(f):
    d=json.loads(line)
    if d.get('type')!='assistant' or d.get('uuid') in seen: continue
    seen.add(d.get('uuid'))
    for c in d['message'].get('content') or []:
        t=''
        if c.get('type')=='text': t=c['text']
        elif c.get('type')=='tool_use' and c['name'] in('SendMessage','Agent','SubagentHandback'): t=c['name']+': '+json.dumps(c['input'],ensure_ascii=False)
        if t and pat.search(t):
            print(d['timestamp'][5:19], t[:int(sys.argv[3]) if len(sys.argv)>3 else 400].replace('\n',' '))
