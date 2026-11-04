# Stream every factory-agent transcript (orchestrator / driver / stack / task driver / integrator)
# plus the main session, and record per assistant message: first/last ts, context size, tools
# (with background flag), and the delivery events (queued_command, resume text, notifications).
# Output: data/B/timelines.pkl  {agent_id: dict(meta, role, msgs=[...], events=[...])}
import json, os, re, glob, pickle, sys
P = os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'B', 'timelines.pkl')

def role(desc):
    d = (desc or '').lower()
    if 'orchestrat' in d or re.match(r'land cr \d+', d): return 'orchestrator'
    if 'stack driver' in d: return 'stack driver'
    if 'integrator' in d: return 'integrator'
    if re.search(r'task driver|cr \d+ t\d+ driver', d): return 'task driver'
    if 'driver' in d: return 'driver'
    if re.search(r'review|critic|re-check|recheck|verify|evidence check', d): return 'reviewer'
    return 'worker'

def parse(path):
    msgs = {}; order = []; events = []
    for line in open(path):
        try: x = json.loads(line)
        except Exception: continue
        t = x.get('type'); ts = x.get('timestamp')
        if not ts: continue
        if t == 'assistant':
            m = x.get('message') or {}
            mid = m.get('id') or x.get('uuid')
            if mid not in msgs:
                msgs[mid] = dict(ts=ts, last=ts, tools=[], ctx=0, model=m.get('model', ''))
                order.append(mid)
            r = msgs[mid]; r['last'] = max(r['last'], ts)
            u = m.get('usage') or {}
            ctx = (u.get('input_tokens') or 0) + (u.get('cache_read_input_tokens') or 0) + (u.get('cache_creation_input_tokens') or 0)
            if ctx: r['ctx'] = ctx; r['cr'] = u.get('cache_read_input_tokens') or 0; r['cw'] = u.get('cache_creation_input_tokens') or 0
            for c in m.get('content') or []:
                if c.get('type') == 'tool_use':
                    i = c.get('input') or {}
                    r['tools'].append((c['name'], bool(i.get('run_in_background')), str(i.get('command') or i.get('description') or i.get('summary') or '')[:120], c.get('id'),
                                       str(i.get('to') or '')))
        elif t == 'attachment':
            a = x.get('attachment') or {}
            if a.get('type') == 'queued_command':
                events.append(('queued', ts, str(a.get('prompt'))[:300]))
        elif t == 'user':
            c = (x.get('message') or {}).get('content')
            txt = c if isinstance(c, str) else ' '.join(z.get('text', '') for z in (c or []) if isinstance(z, dict) and z.get('type') == 'text')
            if txt:
                k = 'notif' if '<task-notification>' in txt else 'agentmsg' if ('<agent-message' in txt or 'sent a message' in txt) else 'usertext'
                events.append((k, ts, txt[:300]))
            if isinstance(c, list):
                for z in c:
                    if isinstance(z, dict) and z.get('type') == 'tool_result':
                        events.append(('result', ts, z.get('tool_use_id')))
    return [dict(id=k, **msgs[k]) for k in order], events

out = {}
for mf in glob.glob(P + '/subagents/*.meta.json'):
    m = json.load(open(mf)); aid = os.path.basename(mf)[:-10]
    ro = role(m.get('description'))
    if ro in ('worker', 'reviewer'): continue
    jf = mf[:-10] + '.jsonl'
    if not os.path.exists(jf): continue
    msgs, ev = parse(jf)
    if not msgs or msgs[-1]['last'] < '2026-10-17': continue
    out[aid] = dict(meta=m, role=ro, msgs=msgs, events=ev)
print('factory agents:', len(out), file=sys.stderr)
msgs, ev = parse(P + '.jsonl')
out['MAIN'] = dict(meta={'description': 'MAIN'}, role='main', msgs=msgs, events=ev)
pickle.dump(out, open(OUT, 'wb'))
import collections
print(collections.Counter(v['role'] for v in out.values()))
