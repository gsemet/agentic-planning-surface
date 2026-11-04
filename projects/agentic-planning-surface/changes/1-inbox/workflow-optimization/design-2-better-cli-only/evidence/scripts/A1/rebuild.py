import json,collections,datetime
exec(open('roles.py').read().split("agg=collections")[0])
rows=[r for r in rows if r['models']]
P={"opus":(4.0,5.0,8.0,0.20,20.0),"sonnet":(2.0,2.5,4.0,0.20,10.0),"haiku":(0.1,0.125,0.2,0.01,0.5),"fable":(10,12.5,20,0.25,50)}
ts=lambda s: datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
res=collections.defaultdict(collections.Counter)
gaps=collections.Counter(); gapcost=collections.Counter()
for r in rows:
    k=role(r); seq=r['seq']
    w1h = r['tokens'].get('w1h',0)>0
    for i,c in enumerate(seq):
        ctx,w,out,t,fam=c; p=P[fam]
        wc = w*(p[2] if w1h else p[1])/1e6
        res[k]['write$']+=wc
        if i==0: res[k]['cold$']+=wc; continue
        gap=(ts(t)-ts(seq[i-1][3])).total_seconds()
        full = w>0.6*ctx and ctx>20000
        if full:
            res[k]['rebuilds']+=1; res[k]['rebuild$']+=wc - (ctx-w)*0  # cost of write
            b='<5min' if gap<300 else '5-15min' if gap<900 else '15-60min' if gap<3600 else '>1h'
            gaps[(k,b)]+=1; gapcost[(k,b)]+=wc
        else:
            res[k]['incr$']+=wc
print('ROLE | write $ | cold-start $ | incremental $ | full rebuilds | rebuild $')
for k,v in sorted(res.items(), key=lambda x:-x[1]['write$']):
    print(f"{k} | {v['write$']:.0f} | {v['cold$']:.0f} | {v['incr$']:.0f} | {v['rebuilds']} | {v['rebuild$']:.0f}")
print('\nrebuilds by gap since previous turn:')
for (k,b),n in sorted(gaps.items()): print(f"  {k:24s} {b:8s} n={n:4d} ${gapcost[(k,b)]:.1f}")
# incremental write size distribution: what drives incremental writes = new content per turn (tool results)
inc=collections.Counter(); incn=collections.Counter()
for r in rows:
    for i,c in enumerate(r['seq'][1:],1):
        ctx,w,out,t,fam=c
        if not (w>0.6*ctx and ctx>20000):
            b='<2k' if w<2e3 else '2-10k' if w<1e4 else '10-30k' if w<3e4 else '>30k'
            inc[b]+=w; incn[b]+=1
print('\nincremental writes per turn: turns / Mtok', {b:(incn[b], round(inc[b]/1e6,1)) for b in ['<2k','2-10k','10-30k','>30k']})
