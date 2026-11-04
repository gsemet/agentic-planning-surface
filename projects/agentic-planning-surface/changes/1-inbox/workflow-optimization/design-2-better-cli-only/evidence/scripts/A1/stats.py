import pickle,collections,statistics,json
rows=pickle.load(open('../facrows.pkl','rb'))
meta={}
for l in open('../meta.tsv'):
    ts,aid,desc,model,depth,typ,sz,tu=l.rstrip('\n').split('\t'); meta[aid]=model
PR={'sonnet':(3,0.3,3.75,15),'opus':(5,0.5,6.25,25),'haiku':(1,0.1,1.25,5)}
def cost(tok,model):
    p=PR.get(model or 'sonnet',PR['sonnet'])
    return (tok.get('input_tokens',0)*p[0]+tok.get('cache_read_input_tokens',0)*p[1]+tok.get('cache_creation_input_tokens',0)*p[2]+tok.get('output_tokens',0)*p[3])/1e6
st=collections.defaultdict(lambda: dict(n=0,main=0,deliv=0,lat=[],tok=collections.Counter(),cost=0.0,turns=0,undeliv=0))
seenb=set()
for r in rows:
    c=st[r['cat']]; c['n']+=1; c['main']+= r['src']=='MAIN'
    if 'deliv' in r:
        c['deliv']+=1; c['lat'].append(r['latency_s'])
        b=(r['fid'],r['deliv'][:19])
        if b not in seenb:
            seenb.add(b); c['tok'].update(r['tok']); c['turns']+=r['turns']; c['cost']+=cost(r['tok'],meta.get(r['fid']))
    else: c['undeliv']+=1
out={}
print('cat n main deliv undeliv medianLat_s p90Lat_s >30min turns tokTotal(M) out(k) cost$')
for k in sorted(st):
    c=st[k]; L=sorted(c['lat'])
    med=statistics.median(L) if L else None; p90=L[int(0.9*(len(L)-1))] if L else None
    tt=sum(c['tok'].values())
    print(k,c['n'],c['main'],c['deliv'],c['undeliv'],int(med) if med is not None else '-',int(p90) if p90 is not None else '-',sum(1 for x in L if x>1800),c['turns'],round(tt/1e6,1),round(c['tok']['output_tokens']/1e3,1),round(c['cost'],1))
    out[k]=dict(n=c['n'],main=c['main'],deliv=c['deliv'],undeliv=c['undeliv'],med=med,p90=p90,slow=sum(1 for x in L if x>1800),turns=c['turns'],tokM=tt/1e6,cost=c['cost'])
json.dump(out,open('../stats.json','w'),indent=1)
# MAIN-only latency
L=sorted(r['latency_s'] for r in rows if r['src']=='MAIN' and 'deliv' in r)
print('MAIN->factory delivered',len(L),'of',sum(1 for r in rows if r['src']=='MAIN'),'median',statistics.median(L),'>30min',sum(1 for x in L if x>1800),'>2h',sum(1 for x in L if x>7200),'<2min',sum(1 for x in L if x<120))
L=sorted(r['latency_s'] for r in rows if r['src']!='MAIN' and 'deliv' in r)
print('agent->agent delivered',len(L),'median',statistics.median(L),'>30min',sum(1 for x in L if x>1800))
