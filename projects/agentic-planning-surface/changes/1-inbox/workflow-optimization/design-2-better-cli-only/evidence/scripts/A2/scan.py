import json,os,sys,collections,pickle
P='/Users/az02065/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a'
files=[('MAIN',P+'.jsonl')]
for f in sorted(os.listdir(P+'/subagents')):
    if f.endswith('.jsonl'): files.append((f[:-6],P+'/subagents/'+f))
toolcount=collections.Counter()
parent={}   # toolUseId -> file id
sends=[]    # SendMessage calls
spawns=[]   # Agent calls
for fid,path in files:
    with open(path) as fh:
        for line in fh:
            try: d=json.loads(line)
            except: continue
            msg=d.get('message') or {}
            if d.get('type')=='assistant' and isinstance(msg.get('content'),list):
                for c in msg['content']:
                    if c.get('type')=='tool_use':
                        n=c.get('name'); toolcount[n]+=1
                        parent[c.get('id')]=fid
                        if n in('SendMessage',):
                            sends.append(dict(ts=d.get('timestamp'),src=fid,input=c.get('input'),id=c.get('id')))
                        if n in('Agent','Task'):
                            spawns.append(dict(ts=d.get('timestamp'),src=fid,input=c.get('input'),id=c.get('id')))
print(toolcount.most_common(40))
print(len(sends),len(spawns))
pickle.dump(dict(parent=parent,sends=sends,spawns=spawns),open('../scan.pkl','wb'))
