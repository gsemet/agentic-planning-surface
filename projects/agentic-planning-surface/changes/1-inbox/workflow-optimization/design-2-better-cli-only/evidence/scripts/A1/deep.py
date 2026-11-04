import json,re,collections,statistics as st
exec(open('roles.py').read().split("agg=collections")[0])
rows=[r for r in rows if r['models']]
P={"opus":(4.0,5.0,8.0,0.20,20.0),"sonnet":(2.0,2.5,4.0,0.20,10.0),"haiku":(0.1,0.125,0.2,0.01,0.5),"fable":(10,12.5,20,0.25,50)}
# 1. cost components
comp=collections.Counter()
for r in rows:
    fam=max(r['models'],key=r['models'].get); p=P[fam]; t=r['tokens']
    comp['cache read']+=t.get('cache_read_input_tokens',0)*p[3]/1e6
    comp['cache write 5m']+=t.get('w5',0)*p[1]/1e6
    comp['cache write 1h']+=t.get('w1h',0)*p[2]/1e6
    comp['uncached input']+=t.get('input_tokens',0)*p[0]/1e6
    comp['output']+=t.get('output_tokens',0)*p[4]/1e6
T=sum(comp.values()); print('COMPONENTS', {k:f"{v:.0f}$ {100*v/T:.0f}%" for k,v in comp.items()}, f"total {T:.0f}")
# 2. per role: turns/agent, median ctx, first-turn write (cold start), growth
print('\nROLE | agents | med turns | p90 turns | med ctx/turn | med first ctx | cold-start $ total | ctx last/first')
for k in ['main (human-facing)','orchestrator','driver','coder/writer','reviewer/critic/audit','analyst/inventory','other']:
    rs=[r for r in rows if role(r)==k and r['seq']]
    turns=[len(r['seq']) for r in rs]
    ctxs=[c[0] for r in rs for c in r['seq']]
    first=[r['seq'][0][0] for r in rs]
    cold=sum(r['seq'][0][1]*P[r['seq'][0][4]][1]/1e6 for r in rs)
    growth=[r['seq'][-1][0]/max(1,r['seq'][0][0]) for r in rs]
    q=lambda a,p: sorted(a)[int(p*(len(a)-1))]
    print(f"{k} | {len(rs)} | {st.median(turns):.0f} | {q(turns,.9)} | {st.median(ctxs)/1e3:.0f}k | {st.median(first)/1e3:.1f}k | {cold:.1f} | {st.median(growth):.1f}x")
# 3. cost by context band (what a turn costs as context grows)
band=collections.Counter(); bandn=collections.Counter()
for r in rows:
    for c in r['seq']:
        b='<50k' if c[0]<50e3 else '50-100k' if c[0]<100e3 else '100-200k' if c[0]<200e3 else '200-400k' if c[0]<400e3 else '>400k'
        p=P[c[4]]; band[b]+=(c[0]-c[1])*p[3]/1e6 + c[1]*p[1]/1e6 + c[2]*p[4]/1e6; bandn[b]+=1
print('\nCTX BAND turns / approx $', {b:(bandn[b], round(band[b])) for b in ['<50k','50-100k','100-200k','200-400k','>400k']})
# 4. tool profile per role
print('\nTOOLS per role (calls)')
for k in ['main (human-facing)','orchestrator','driver','coder/writer','reviewer/critic/audit','analyst/inventory']:
    tc=collections.Counter(); bc=collections.Counter(); rc=collections.Counter(); rd=collections.Counter()
    for r in rows:
        if role(r)!=k: continue
        tc.update(r['tools']); bc.update(r['bash']); rc.update(r['result_chars']); rd.update(r['reads'])
    print(k, dict(tc.most_common(8)), '| bash', dict(bc.most_common(9)), '| result MB', {a:round(b/1e6,1) for a,b in rc.most_common(5)}, '| rule reads', rd.get('rules',0), '/', rd.get('all',0))
