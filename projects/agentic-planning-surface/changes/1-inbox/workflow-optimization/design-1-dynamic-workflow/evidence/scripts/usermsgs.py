import json,collections
P='/Users/az02065/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a.jsonl'
out=open('../usermsgs.tsv','w'); seen=set(); kinds=collections.Counter()
with open(P) as fh:
    for line in fh:
        d=json.loads(line)
        if d.get('type')!='user' or d.get('isMeta'): continue
        ts=d.get('timestamp','')
        if ts<'2026-10-17': continue
        c=(d.get('message') or {}).get('content')
        if isinstance(c,list):
            texts=[x.get('text','') for x in c if x.get('type')=='text']
            if not texts: continue
            t='\n'.join(texts)
        else: t=c or ''
        if d.get('uuid') in seen: continue
        seen.add(d.get('uuid'))
        k='notif' if '<task-notification' in t else ('cmd' if t.startswith('<command') or t.startswith('<local-command') else ('sys' if t.startswith('<system-reminder') else 'user'))
        kinds[k]+=1
        if k=='user':
            out.write(f"{ts[:19]}\t{d.get('uuid')}\t{t.replace(chr(10),' ⏎ ')[:600]}\n")
print(kinds)
