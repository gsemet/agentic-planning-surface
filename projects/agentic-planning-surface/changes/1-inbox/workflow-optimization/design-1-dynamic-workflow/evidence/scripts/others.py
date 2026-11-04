import json,os,glob,collections
R=os.path.expanduser('~/.claude/projects')
for path in glob.glob(R+'/*/*.jsonl'):
    if 'c985a2ca' in path or 'dd375646' in path: continue
    if os.path.getmtime(path)< 1760659200+86400*365: pass
    import time
    if os.path.getmtime(path) < time.mktime((2026,10,17,0,0,0,0,0,-1)): continue
    c=collections.Counter(); first=None; cwd=None
    with open(path) as fh:
        for line in fh:
            try:d=json.loads(line)
            except: continue
            first=first or d.get('timestamp'); cwd=cwd or d.get('cwd')
            m=d.get('message') or {}
            if d.get('type')=='assistant' and isinstance(m.get('content'),list):
                for x in m['content']:
                    if x.get('type')=='tool_use': c[x['name']]+=1
    sub=path[:-6]+'/subagents'
    ns=len(os.listdir(sub))//2 if os.path.isdir(sub) else 0
    if c['SendMessage'] or c['Agent'] or ns:
        print(os.path.basename(os.path.dirname(path))[-40:],os.path.basename(path)[:8],first,cwd,'send',c['SendMessage'],'agent',c['Agent'],'subs',ns)
