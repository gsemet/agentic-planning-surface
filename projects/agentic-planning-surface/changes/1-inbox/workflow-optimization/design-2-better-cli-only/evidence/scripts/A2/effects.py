import json,pickle,os,re,collections,datetime
P='/Users/az02065/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a'
d=pickle.load(open('../scan.pkl','rb'))
meta={}
for l in open('../meta.tsv'):
    ts,aid,desc,model,depth,typ,sz,tu=l.rstrip('\n').split('\t')
    meta[aid]=dict(ts=ts,desc=desc,model=model,depth=depth)
def path(fid): return P+'.jsonl' if fid=='MAIN' else P+'/subagents/'+fid+'.jsonl'
def T(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
sends=[s for s in d['sends'] if s['ts']>='2026-10-17']
ids={s['id'] for s in sends}
# tool results
res={}
bysrc=collections.defaultdict(list)
for s in sends: bysrc[s['src']].append(s)
for src in bysrc:
    for line in open(path(src)):
        if 'tool_result' not in line: continue
        try: x=json.loads(line)
        except: continue
        m=x.get('message') or {}
        if x.get('type')!='user' or not isinstance(m.get('content'),list): continue
        for c in m['content']:
            if c.get('type')=='tool_result' and c.get('tool_use_id') in ids:
                cc=c.get('content'); 
                if isinstance(cc,list): cc=' '.join(z.get('text','') for z in cc if isinstance(z,dict))
                res[c['tool_use_id']]=str(cc)[:300]
# recipient index
def norm(t): return re.sub(r'\s+',' ',t or '')[:700]
recips=collections.defaultdict(list)
for s in sends:
    to=str(s['input'].get('to') or s['input'].get('recipient'))
    fid=to if to.startswith('agent-') else 'agent-'+to
    s['fid']=fid
    if os.path.exists(path(fid)): recips[fid].append(s)
idx={}
for fid in recips:
    events=[]
    seen=set()
    for line in open(path(fid)):
        try: x=json.loads(line)
        except: continue
        if x.get('type')=='api-request-blob': continue
        u=x.get('uuid')
        if u in seen: continue
        seen.add(u)
        ts=x.get('timestamp')
        if not ts: continue
        if x.get('type')=='attachment':
            a=x.get('attachment') or {}
            if a.get('type')=='queued_command':
                events.append(('deliv',ts,norm(str(a.get('prompt')))))
        elif x.get('type')=='user':
            c=(x.get('message') or {}).get('content')
            if isinstance(c,str): events.append(('deliv',ts,norm(c)))
            elif isinstance(c,list):
                for z in c:
                    if z.get('type')=='text': events.append(('deliv',ts,norm(z.get('text'))))
        elif x.get('type')=='assistant':
            m=x.get('message') or {}
            us=m.get('usage') or {}
            tools=[]
            for z in m.get('content') or []:
                if z.get('type')=='tool_use':
                    i=z.get('input') or {}
                    brief=i.get('description') or i.get('summary') or i.get('command') or i.get('file_path') or ''
                    tools.append(f"{z['name']}:{str(brief)[:90]}")
                elif z.get('type')=='text' and z.get('text','').strip():
                    tools.append('TXT:'+z['text'][:90].replace('\n',' '))
            events.append(('asst',ts,tools,us,m.get('id')))
    idx[fid]=events
out=[]
dmap={}
for s in sorted(sends,key=lambda z:z['ts']):
    fid=s['fid']; ev=idx.get(fid)
    if not ev: continue
    key=norm(str(s['input'].get('message')))[:50]
    di=None
    for k,e in enumerate(ev):
        if e[0]=='deliv' and e[1]>=s['ts'][:19] and key in e[2]: di=k;break
    if di is None:
        for k,e in enumerate(ev):
            if e[0]=='deliv' and key[:40] in e[2]: di=k;break
    if di is not None: dmap[s['id']]=di
dset=collections.defaultdict(set)
for s in sends:
    if s['id'] in dmap: dset[s['fid']].add(dmap[s['id']])
for s in sorted(sends,key=lambda z:z['ts']):
    fid=s['fid']
    r=dict(id=s['id'],ts=s['ts'],src=s['src'],fid=fid,summary=s['input'].get('summary',''),msg=str(s['input'].get('message')),result=res.get(s['id'],''))
    ev=idx.get(fid)
    if s['id'] in dmap:
        di=dmap[s['id']]
        r['deliv']=ev[di][1]
        r['latency_s']=(T(ev[di][1])-T(s['ts'])).total_seconds()
        acts=[];tok=collections.Counter();mids=set();last=ev[di][1]
        for k in range(di+1,len(ev)):
            e=ev[k]
            if k in dset[fid] and (T(e[1])-T(ev[di][1])).total_seconds()>5: break
            if e[0]=='asst':
                if (T(e[1])-T(ev[di][1])).total_seconds()>3600: break
                last=e[1]; acts.extend(e[2])
                if e[4] not in mids:
                    mids.add(e[4])
                    for k2 in('input_tokens','cache_read_input_tokens','cache_creation_input_tokens','output_tokens'):
                        tok[k2]+=e[3].get(k2,0) or 0
        r['acts']=acts[:14]; r['turns']=len(mids); r['tok']=dict(tok); r['span_s']=(T(last)-T(ev[di][1])).total_seconds()
        r['batch']=sum(1 for z in dset[fid] if abs((T(ev[z][1])-T(ev[di][1])).total_seconds())<=5)
    out.append(r)
pickle.dump(out,open('../effects.pkl','wb'))
print(len(out), sum(1 for r in out if 'deliv' in r))
import sys
if len(sys.argv)>1:
    sid=[s for s in sends if s['input'].get('summary')==sys.argv[1]][0]
    fid=sid['fid']; ev=idx[fid]; di=dmap[sid['id']]
    print(di, sorted(dset[fid])[:50])
    for k in range(di-1,di+6): print(k, ev[k][0],ev[k][1],str(ev[k][2])[:150])
