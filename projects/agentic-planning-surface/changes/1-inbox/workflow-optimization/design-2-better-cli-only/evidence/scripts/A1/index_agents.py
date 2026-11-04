import json, os, sys, glob, collections
base=os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a/subagents')
out=sys.argv[1]
rows=[]
for m in glob.glob(base+'/*.meta.json'):
    aid=os.path.basename(m)[:-10]
    meta=json.load(open(m))
    j=base+'/'+aid+'.jsonl'
    first=last=None; n=0; nasst=0
    if os.path.exists(j):
        with open(j) as f:
            for line in f:
                try: d=json.loads(line)
                except: continue
                ts=d.get('timestamp')
                if ts:
                    first=first or ts; last=ts
                if d.get('type')=='assistant': nasst+=1
    rows.append(dict(id=aid, desc=meta.get('description'), model=meta.get('model'), parent=meta.get('parentAgentId'), depth=meta.get('spawnDepth'), shape=meta.get('requestShape'), first=first, last=last, nasst=nasst, size=os.path.getsize(j) if os.path.exists(j) else 0, type=meta.get('agentType')))
json.dump(rows, open(out,'w'), indent=0)
print(len(rows))
