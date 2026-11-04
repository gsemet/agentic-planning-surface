import json,sys
def rows(path, since=None):
    seen=set()
    for line in open(path):
        try: d=json.loads(line)
        except: continue
        if d.get('type')!='assistant': continue
        m=d.get('message',{}); u=m.get('usage');
        if not u: continue
        mid=m.get('id')
        if mid in seen: continue
        seen.add(mid)
        ts=d.get('timestamp','')
        if since and ts<since: continue
        cc=u.get('cache_creation') or {}
        yield ts[11:19], m.get('model','')[:16], u.get('input_tokens',0), cc.get('ephemeral_5m_input_tokens',0), cc.get('ephemeral_1h_input_tokens',0), u.get('cache_creation_input_tokens',0), u.get('cache_read_input_tokens',0), u.get('output_tokens',0)
since=sys.argv[2] if len(sys.argv)>2 else None
print("time(UTC) model in w5m w1h wtot read out")
for r in rows(sys.argv[1], since): print(*r)
