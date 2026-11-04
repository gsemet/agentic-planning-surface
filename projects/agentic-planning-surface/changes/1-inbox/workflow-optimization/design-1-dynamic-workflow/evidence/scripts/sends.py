import json,pickle,collections
d=pickle.load(open('../scan.pkl','rb'))
meta={}
for l in open('../meta.tsv'):
    ts,aid,desc,model,depth,typ,sz,tu=l.rstrip('\n').split('\t')
    meta[aid]=dict(ts=ts,desc=desc,model=model,depth=depth,tu=tu)
def name(fid):
    if fid=='MAIN': return 'MAIN'
    m=meta.get(fid,{}); return f"{m.get('desc')}[{m.get('depth')}]"
print(collections.Counter(s['input'].keys().__repr__() for s in d['sends']))
c=collections.Counter((s['src'] if s['src']=='MAIN' else 'depth'+meta.get(s['src'],{}).get('depth','?')) for s in d['sends']); print(c)
c=collections.Counter(s['ts'][:10] for s in d['sends']); print(sorted(c.items()))
