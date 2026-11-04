import json,pickle,collections
d=pickle.load(open('../scan.pkl','rb'))
meta={}
for l in open('../meta.tsv'):
    ts,aid,desc,model,depth,typ,sz,tu=l.rstrip('\n').split('\t')
    meta[aid]=dict(ts=ts,desc=desc,model=model,depth=depth,tu=tu)
def name(fid):
    if fid=='MAIN': return 'MAIN'
    m=meta.get(fid,{}); return f"{m.get('desc')}[d{m.get('depth')}]"
out=open('../sends.tsv','w')
n=0
for s in sorted(d['sends'],key=lambda x:x['ts']):
    if s['ts']<'2026-10-17': continue
    i=s['input']; to=str(i.get('to') or i.get('recipient'))
    fid='agent-'+to if not to.startswith('agent-') else to
    dst=name(fid) if fid in meta else 'UNRESOLVED:'+to
    msg=str(i.get('message') or i.get('content')).replace('\n',' ⏎ ')
    n+=1
    out.write(f"{n}\t{s['ts'][:19]}\t{name(s['src'])}\t{s['src']}\t{dst}\t{fid}\t{i.get('summary','')}\t{msg[:400]}\n")
print(n)
