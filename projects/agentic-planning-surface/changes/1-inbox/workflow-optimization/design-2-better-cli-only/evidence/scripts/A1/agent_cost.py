import json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(__file__))
base = os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a/subagents/')
PRICE = {'opus': (4.0, 5.0, 8.0, 0.20, 20.0), 'sonnet': (2.0, 2.5, 4.0, 0.20, 10.0), 'haiku': (0.10, 0.125, 0.20, 0.01, 0.50), 'fable': (4.0, 5.0, 8.0, 0.20, 20.0)}
def fam(m):
    for k in PRICE:
        if k in (m or ''): return k
    return 'sonnet'
def cost(u, m):
    p = PRICE[fam(m)]; cc = u.get('cache_creation') or {}
    w5 = cc.get('ephemeral_5m_input_tokens', 0) or 0; w1 = cc.get('ephemeral_1h_input_tokens', 0) or 0
    if not cc: w5 = u.get('cache_creation_input_tokens', 0) or 0
    return (u.get('input_tokens', 0)*p[0] + w5*p[1] + w1*p[2] + u.get('cache_read_input_tokens', 0)*p[3] + u.get('output_tokens', 0)*p[4]) / 1e6
rows = json.load(open('agents.json'))
ROLE = [('orchestrator', r'orchestr|supervis|restart|Land CR'), ('stack driver', r'stack driver|Stack driver'), ('integrator', r'integrator'),
        ('task driver', r'task driver|T\d+ driver'), ('CR driver', r'driver'), ('conflict fixer', r'conflict|rebase'),
        ('coder', r'coder|implement|Fix '), ('reviewer', r'review|critic|evidence check'), ]
def role(d):
    for n, p in ROLE:
        if re.search(p, d, re.I): return n
    return 'other'
agg = collections.Counter(); turns = collections.Counter(); n = collections.Counter()
for r in rows:
    if not r['first'] or r['last'] < '2026-10-22T16:00' or r['first'] < '2026-10-22T16:00': continue
    msgs = {}
    for line in open(base + r['id'] + '.jsonl'):
        if '"assistant"' not in line[:300] and '"type":"assistant"' not in line: continue
        d = json.loads(line)
        if d.get('type') != 'assistant': continue
        m = d['message']
        if m.get('model') == '<synthetic>': continue
        msgs[m.get('id')] = (m.get('usage', {}), m.get('model'))
    c = sum(cost(u, mo) for u, mo in msgs.values())
    k = role(r['desc'] or ''); agg[k] += c; turns[k] += len(msgs); n[k] += 1
tot = sum(agg.values())
for k, v in agg.most_common(): print(f"{k:15s} agents {n[k]:4d} turns {turns[k]:6d} ${v:8.2f} {100*v/tot:5.1f}%")
print('total', round(tot, 2))
