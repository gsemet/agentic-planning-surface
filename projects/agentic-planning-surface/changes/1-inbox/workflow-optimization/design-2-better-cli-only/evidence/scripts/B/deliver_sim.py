# Real delivery delays of factory messages vs. design-2 simulation.
# Inputs: research/facrows.pkl (232 classified factory sends, design-1), data/B/timelines.pkl, data/B/gaps.pkl
import pickle, os, datetime, collections, statistics, bisect, json, sys
H = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(H, '..', '..', 'data', 'B')
R1 = os.path.join(H, '..', '..', '..', 'research')
rows = pickle.load(open(os.path.join(R1, 'facrows.pkl'), 'rb'))
tl = pickle.load(open(os.path.join(D, 'timelines.pkl'), 'rb'))
def T(s): return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
sys.path.insert(0, H)
from gaps import kind  # noqa
PRICE = {'opus': (4.0, 5.0, 8.0, 0.20, 20.0), 'sonnet': (2.0, 2.5, 4.0, 0.20, 10.0), 'haiku': (0.10, 0.125, 0.20, 0.01, 0.50)}
WAKE = 5.0  # seconds: crf wait polls the mailbox, exits, harness notifies, next turn starts
BASHW = {'fg-bash-wait', 'fg-bash-gate', 'fg-bash-other', 'monitor', 'taskoutput', 'other-tool'}
AGENTW = {'agent-call'}
out = []
for r in rows:
    a = tl.get(r['fid'])
    if not a or a['role'] == 'main': continue
    s = r['ts']; ms = a['msgs']
    lat = float(r['latency_s']) if r.get('deliv') else None
    if r['n'] in (282, '282', 283, '283') and lat is None:
        lat = (T('2026-10-27T21:56:16Z') - T(s)).total_seconds()  # delivered with the 21:56:16 hand-back batch (checked 22:15Z)
    st = None; nxt = None; prev = None
    for i, m in enumerate(ms):
        if m['ts'] <= s <= m['last']: st = 'mid-turn'; nxt = ms[i + 1]['ts'] if i + 1 < len(ms) else None; prev = m; break
        if i + 1 < len(ms) and m['last'] < s < ms[i + 1]['ts']:
            st = kind(m['tools']); nxt = ms[i + 1]['ts']; prev = m; break
    if st is None:
        st = 'before-start' if s < ms[0]['ts'] else 'after-end'; prev = ms[-1] if st == 'after-end' else None
    # design-2 simulation
    if lat is None:
        sim_naive = sim_real = None  # never delivered: handled separately (restart from state)
    elif st in BASHW:
        sim_naive = sim_real = min(lat, WAKE)
    elif st in AGENTW:
        sim_naive = min(lat, WAKE); sim_real = lat   # nested Agent calls hold the round open
    else:
        sim_naive = sim_real = lat                   # mid-turn, resume after hand-back, etc.
    woke = lat is not None and sim_naive is not None and sim_naive < lat - 30 and st not in ('mid-turn',)
    idle = (T(s) - T(prev['last'])).total_seconds() if prev else None
    ctx = prev.get('ctx', 0) if prev else 0
    fam = 'opus' if prev and 'opus' in prev.get('model', '') else 'sonnet'
    p = PRICE[fam]
    cost_rebuild = ctx / 1e6 * p[1]; cost_read = ctx / 1e6 * p[3]
    wake_cost = (cost_rebuild if (idle or 0) > 300 else cost_read) + cost_read + 600 / 1e6 * p[4]  # wake turn + re-arm turn + ~600 output tokens
    out.append(dict(n=r['n'], cat=r['cat'], src=r['src'], srcn=r['srcn'], dst=a['role'], dstn=r['dstn'], fid=r['fid'], ts=s, summary=r['summary'],
                    state=st, lat=lat, sim_naive=sim_naive, sim_real=sim_real, woke=woke, wake_ctx=ctx, idle=idle, fam=fam, wake_cost=wake_cost if woke else 0,
                    real_wait_rebuild=(idle or 0) > 300))
pickle.dump(out, open(os.path.join(D, 'deliver_sim.pkl'), 'wb'))
def f(x):
    if x is None: return '-'
    return f'{x:.0f}s' if x < 120 else f'{x/60:.1f}m' if x < 7200 else f'{x/3600:.1f}h'
def summ(sel, label):
    lat = [o['lat'] for o in sel if o['lat'] is not None]
    nn = [o['sim_naive'] for o in sel if o['sim_naive'] is not None]
    rr = [o['sim_real'] for o in sel if o['sim_real'] is not None]
    nd = sum(1 for o in sel if o['lat'] is None)
    def line(v): return f"{f(statistics.median(v)) if v else '-'} / {f(sorted(v)[int(.9*len(v))]) if v else '-'} / {sum(1 for x in v if x>1800)}"
    print(f'| {label} | {len(sel)} | {nd} | {line(lat)} | {line(nn)} | {line(rr)} |')
print('Delays: median / p90 / count >30 min. "naive" = every wait is a background crf wait (seconds); "real" = nested Agent calls still hold the tool round open.')
print('| Messages | n | never delivered | today | design 2 naive | design 2 with blocking Agent calls |')
print('|---|---|---|---|---|---|')
DYN = lambda o: not o['cat'].startswith(('K_', 'L_'))
summ([o for o in out if o['src'] == 'MAIN' and o['dst'] == 'orchestrator'], 'main → orchestrator (all)')
summ([o for o in out if o['src'] == 'MAIN' and o['dst'] != 'orchestrator'], 'main → driver/stack/task')
summ([o for o in out if o['src'] != 'MAIN' and o['dst'] == 'orchestrator'], 'agent → orchestrator')
summ([o for o in out if o['src'] != 'MAIN' and o['dst'] != 'orchestrator'], 'orchestrator → driver/stack/task')
summ([o for o in out if DYN(o)], 'all dynamic (cat A–M)')
summ(out, 'all to factory roles')
print()
print('Recipient state at send time:')
c = collections.Counter((o['dst'] if o['dst']=='orchestrator' else 'driver-kind', o['state'], 'delivered' if o['lat'] is not None else 'never') for o in out)
for k in sorted(c): print(' ', k, c[k])
# wake-ups
w = [o for o in out if o['woke']]
# dedupe: same recipient within 60 s
w.sort(key=lambda o: (o['fid'], o['ts'])); ded = []; last = {}
for o in w:
    if o['fid'] in last and (T(o['ts']) - T(last[o['fid']])).total_seconds() < 60: continue
    ded.append(o); last[o['fid']] = o['ts']
print()
print(f'Extra wake-ups (naive): {len(w)} messages, {len(ded)} wake-ups after 60 s dedupe;'
      f' rebuilds {sum(1 for o in ded if o["real_wait_rebuild"])}; median context {statistics.median([o["wake_ctx"] for o in ded])/1000:.0f}k;'
      f' cost ${sum(o["wake_cost"] for o in ded):.2f}')
wr = [o for o in ded if o['state'] in BASHW]
print(f'Extra wake-ups (blocking Agent calls): {len(wr)}; cost ${sum(o["wake_cost"] for o in wr):.2f}')
for o in sorted(ded, key=lambda o: -o['wake_cost'])[:8]:
    print('   ', o['ts'][5:16], o['dst'], o['dstn'][:30], o['state'], f(o['idle']), f'{o["wake_ctx"]/1000:.0f}k', o['fam'], f'${o["wake_cost"]:.2f}')

# ---- never-delivered messages: state of the recipient and time until a replacement started
import glob
P = os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a')
starts = []
for aid, a in tl.items():
    if aid != 'MAIN' and a['role'] == 'orchestrator' and a['meta'].get('spawnDepth') == 1:
        starts.append((a['msgs'][0]['ts'], aid, a['meta'].get('description', '')))
starts.sort()
print()
print('Never delivered:')
print('| # | sent | to | summary | recipient last tools | replacement started | delay to replacement |')
print('|---|---|---|---|---|---|---|')
for o in out:
    if o['lat'] is not None: continue
    a = tl[o['fid']]; lm = a['msgs'][-1]
    lk = kind(lm['tools']) if o['state'] == 'after-end' else o['state']
    o['never_state'] = lk
    rep = next(((s, aid, d) for s, aid, d in starts if s > o['ts'] and aid != o['fid']), None)
    o['replacement_s'] = (T(rep[0]) - T(o['ts'])).total_seconds() if rep else None
    print(f"| {o['n']} | {o['ts'][5:16]} | {o['dstn'][:32]} | {o['summary'][:50]} | {lk} (last turn {lm['last'][5:16]}) | {rep[0][5:16] + ' ' + rep[2][:30] if rep else '-'} | {f(o['replacement_s'])} |")
pickle.dump(out, open(os.path.join(D, 'deliver_sim.pkl'), 'wb'))

# ---- extra wake-ups per child completion if spawns were non-blocking (design 2 naive)
ab = pickle.load(open(os.path.join(D, 'agent_block.pkl'), 'rb'))
bat = collections.defaultdict(list)
for r in ab:
    if r['role'] in ('orchestrator', 'driver', 'stack driver', 'task driver') and r['dur']:
        bat[(r['src'], r['ts'][:16])].append(r)  # parallel calls of one message share the minute
multi = [v for v in bat.values() if len(v) > 1]
extra = sum(len(v) - 1 for v in multi)
print()
print(f'Parallel spawn batches in factory roles: {len(multi)} batches with >1 child, {sum(len(v) for v in multi)} children;'
      f' today 1 wake per batch, design 2 naive 1 wake per child: +{extra} wakes')
# cost: context of the spawning agent at that time
ce = 0.0; n = 0
for v in multi:
    a = tl.get(v[0]['src']);
    if not a: continue
    m = next((m for m in a['msgs'] if m['ts'] <= v[0]['ts'] <= m['last'] or m['ts'] >= v[0]['ts']), None)
    if not m: continue
    ctx = m.get('ctx', 0); fam = 'opus' if 'opus' in m.get('model', '') else 'sonnet'; p = PRICE[fam]
    durs = sorted(x['dur'] for x in v)
    for k in range(1, len(durs)):
        gapk = durs[k - 1] - (durs[k - 2] if k >= 2 else 0)
        ce += ctx / 1e6 * (p[1] if gapk > 300 else p[3]) + ctx / 1e6 * p[3] + 400 / 1e6 * p[4]; n += 1
print(f'  estimated cost of those extra wakes: ${ce:.2f} over {n} wakes')
