import json,sys
for line in open(sys.argv[1]):
    try: d=json.loads(line)
    except: continue
    ts=d.get('timestamp','')[11:19]; t=d.get('type')
    m=d.get('message',{})
    c=m.get('content') if isinstance(m,dict) else None
    if isinstance(c,str): print(ts,t,'TEXT',c[:220].replace('\n',' ')); continue
    for b in c or []:
        k=b.get('type')
        if k=='tool_use': print(ts,t,'USE',b.get('name'),json.dumps(b.get('input'))[:220])
        elif k=='tool_result':
            r=b.get('content'); r=r if isinstance(r,str) else json.dumps(r)
            print(ts,t,'RES',r[:260].replace('\n',' '))
        elif k=='text': print(ts,t,'TEXT',b.get('text','')[:220].replace('\n',' '))
