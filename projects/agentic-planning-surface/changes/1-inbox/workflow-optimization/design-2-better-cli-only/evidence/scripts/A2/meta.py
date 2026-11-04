import json,os,sys,collections
S='/Users/az02065/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a/subagents'
rows=[]
for f in os.listdir(S):
    if f.endswith('.meta.json'):
        m=json.load(open(os.path.join(S,f)))
        aid=f[:-10]
        sz=os.path.getsize(os.path.join(S,aid+'.jsonl')) if os.path.exists(os.path.join(S,aid+'.jsonl')) else 0
        # first timestamp
        ts=None
        try:
            with open(os.path.join(S,aid+'.jsonl')) as fh:
                for line in fh:
                    d=json.loads(line); ts=d.get('timestamp');
                    if ts: break
        except Exception: pass
        rows.append((ts or '',aid,m.get('description'),m.get('model'),m.get('spawnDepth'),m.get('agentType'),sz,m.get('toolUseId')))
rows.sort()
with open('../meta.tsv','w') as o:
    for r in rows: o.write('\t'.join(map(str,r))+'\n')
c=collections.Counter(r[4] for r in rows); print(c)
print(collections.Counter(r[0][:10] for r in rows))
