import pickle,re,sys
out=pickle.load(open('../effects.pkl','rb'))
meta={}
for l in open('../meta.tsv'):
    ts,aid,desc,model,depth,typ,sz,tu=l.rstrip('\n').split('\t'); meta[aid]=(desc,model,depth)
rx=re.compile(r'orchestr|driver|integrat|stack|Orchestrate',re.I)
def nm(f): return 'MAIN' if f=='MAIN' else (meta.get(f,('?',))[0] if f in meta else f)
n=0
rows=[]
for k,r in enumerate(out,1):
    src=nm(r['src']); dst=nm(r['fid'])
    if not (rx.search(src) or rx.search(dst)): continue
    r['n']=k; r['srcn']=src; r['dstn']=dst
    rows.append(r)
pickle.dump(rows,open('../facrows.pkl','wb'))
mode=sys.argv[1]
for r in rows:
    if mode=='main' and r['src']!='MAIN': continue
    if mode=='agent' and r['src']=='MAIN': continue
    lat=r.get('latency_s'); tok=r.get('tok',{})
    tt=sum(tok.values()) if tok else 0
    print(f"#{r['n']} {r['ts'][5:16]} {r['srcn'][:28]} -> {r['dstn'][:30]} | {r['summary'][:60]}")
    print(f"   deliv={'NO' if lat is None else str(int(lat))+'s'} turns={r.get('turns')} span={int(r.get('span_s',0))}s tok={tt} out={tok.get('output_tokens')}")
    print('   acts:',' ; '.join(a[:70] for a in r.get('acts',[])[:9]))
