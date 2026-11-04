# For each Agent tool call in the main session and in factory agents: requested background flag,
# how long the tool round stayed open (tool_use -> tool_result), and the result kind.
import json, glob, os, re, collections, datetime, statistics, pickle
P = os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a')
def T(s): return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
def role(desc):
    d = (desc or '').lower()
    if 'orchestrat' in d or re.match(r'land cr \d+', d): return 'orchestrator'
    if 'stack driver' in d: return 'stack driver'
    if 'integrator' in d: return 'integrator'
    if re.search(r'task driver|cr \d+ t\d+ driver', d): return 'task driver'
    if 'driver' in d: return 'driver'
    return 'other'
files = [('MAIN', 'main', 0, P + '.jsonl')]
for mf in glob.glob(P + '/subagents/*.meta.json'):
    m = json.load(open(mf)); files.append((os.path.basename(mf)[:-10], role(m.get('description')), m.get('spawnDepth'), mf[:-10] + '.jsonl'))
rows = []
for aid, ro, depth, jf in files:
    if not os.path.exists(jf): continue
    if ro == 'other' and depth != 3: pass
    pend = {}
    with open(jf) as fh:
        for line in fh:
            if '"Agent"' not in line and 'tool_result' not in line: continue
            try: x = json.loads(line)
            except Exception: continue
            m = x.get('message') or {}
            cont = m.get('content') if isinstance(m.get('content'), list) else []
            for z in cont:
                if z.get('type') == 'tool_use' and z.get('name') in ('Agent', 'Task'):
                    pend[z['id']] = (x.get('timestamp'), z['input'].get('run_in_background'), z['input'].get('description', ''))
                elif z.get('type') == 'tool_result' and z.get('tool_use_id') in pend:
                    ts0, bg, desc = pend.pop(z['tool_use_id'])
                    cc = z.get('content'); cc = ' '.join(q.get('text', '') for q in cc if isinstance(q, dict)) if isinstance(cc, list) else str(cc)
                    if re.search(r'Async agent launched|is running in the background|launched successfully', cc[:400], re.I): k = 'async'
                    elif z.get('is_error'): k = 'error'
                    else: k = 'returned-report'
                    rows.append(dict(src=aid, role=ro, depth=depth, ts=ts0, bg=str(bg), dur=(T(x['timestamp']) - T(ts0)).total_seconds() if ts0 and x.get('timestamp') else None, kind=k, desc=desc, res=cc[:160]))
    for k, v in pend.items(): rows.append(dict(src=aid, role=ro, depth=depth, ts=v[0], bg=str(v[1]), dur=None, kind='never-returned', desc=v[2], res=''))
rows = [r for r in rows if (r['ts'] or '') >= '2026-10-17']
pickle.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'B', 'agent_block.pkl'), 'wb'))
c = collections.defaultdict(list)
for r in rows: c[(r['role'], r['bg'], r['kind'])].append(r['dur'] or 0)
print('| Spawner role | run_in_background | Result | n | median open | p90 | max |')
print('|---|---|---|---|---|---|---|')
def f(s): return f'{s:.0f}s' if s < 120 else f'{s/60:.1f}m'
for k in sorted(c):
    v = sorted(c[k]); print(f'| {k[0]} | {k[1]} | {k[2]} | {len(v)} | {f(statistics.median(v))} | {f(v[int(.9*len(v))])} | {f(v[-1])} |')
for r in rows:
    if r['kind'] == 'error': print('ERR', r['role'], r['ts'], r['desc'][:40], r['res'][:150])
