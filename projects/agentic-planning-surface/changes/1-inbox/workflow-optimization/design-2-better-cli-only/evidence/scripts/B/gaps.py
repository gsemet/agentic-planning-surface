# Idle gaps between tool rounds for factory agents, by role and by what the agent was waiting on.
import pickle, os, re, datetime, collections, statistics, json
H = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(H, '..', '..', 'data', 'B')
tl = pickle.load(open(os.path.join(D, 'timelines.pkl'), 'rb'))
def T(s): return datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
WAITRX = re.compile(r'\bsleep\b|--watch|gh run watch|wait\.sh|until |while ', re.I)
GATERX = re.compile(r'just |npm |npx |xvfb|test|gate|preflight|vitest|playwright|ci\b', re.I)
def kind(tools):
    if not tools: return 'turn-ended'
    names = [t[0] for t in tools]
    # In subagents every Agent call holds the tool round open until the child hands back
    # (measured: 0 async launches out of 793 nested spawns, see agent_block.py)
    if any(n in ('Agent', 'Task') for n, bg, *_ in tools): return 'agent-call'
    if any(n == 'SubagentHandback' for n in names): return 'handback'
    fgb = [t for t in tools if t[0] == 'Bash' and not t[1]]
    if any(WAITRX.search(t[2]) for t in fgb): return 'fg-bash-wait'
    if any(GATERX.search(t[2]) for t in fgb): return 'fg-bash-gate'
    if 'Monitor' in names: return 'monitor'
    if 'TaskOutput' in names or 'BashOutput' in names: return 'taskoutput'
    if fgb: return 'fg-bash-other'
    return 'other-tool'
def main():
  rows = []
  for aid, a in tl.items():
      if aid == 'MAIN': continue
      ms = a['msgs']
      for i in range(len(ms) - 1):
          g = (T(ms[i + 1]['ts']) - T(ms[i]['last'])).total_seconds()
          rows.append(dict(aid=aid, role=a['role'], kind=kind(ms[i]['tools']), gap=g, start=ms[i]['last'], end=ms[i + 1]['ts'], ctx=ms[i].get('ctx', 0)))
  pickle.dump(rows, open(os.path.join(D, 'gaps.pkl'), 'wb'))
  def pct(v, p):
      v = sorted(v); return v[min(len(v) - 1, int(p * len(v)))] if v else 0
  def fmt(s):
      return f'{s:.0f}s' if s < 120 else f'{s/60:.1f}m' if s < 7200 else f'{s/3600:.1f}h'
  roles = ['orchestrator', 'driver', 'stack driver', 'task driver', 'integrator']
  print('| Role | Agents | Gaps | p50 | p90 | p99 | max | >5 min | >30 min | wall time in gaps >5 min |')
  print('|---|---|---|---|---|---|---|---|---|---|')
  for ro in roles + ['ALL']:
      v = [r['gap'] for r in rows if ro == 'ALL' or r['role'] == ro]
      n_ag = len({r['aid'] for r in rows if ro == 'ALL' or r['role'] == ro})
      tot = sum(v); big = sum(x for x in v if x > 300)
      print(f'| {ro} | {n_ag} | {len(v)} | {fmt(pct(v,.5))} | {fmt(pct(v,.9))} | {fmt(pct(v,.99))} | {fmt(max(v))} | {sum(1 for x in v if x>300)} | {sum(1 for x in v if x>1800)} | {big/3600:.0f} h of {tot/3600:.0f} h ({100*big/max(tot,1):.0f} %) |')
  print()
  print('Gaps over 5 min, by what the agent was waiting on (orchestrators+drivers of all kinds)')
  print('| Waiting on | n >5 min | median | max | hours |')
  print('|---|---|---|---|---|')
  c = collections.defaultdict(list)
  for r in rows:
      if r['gap'] > 300: c[r['kind']].append(r['gap'])
  for k, v in sorted(c.items(), key=lambda x: -sum(x[1])):
      print(f'| {k} | {len(v)} | {fmt(statistics.median(v))} | {fmt(max(v))} | {sum(v)/3600:.1f} |')
  print()
  for ro in ['orchestrator', 'driver']:
      c = collections.defaultdict(list)
      for r in rows:
          if r['gap'] > 300 and r['role'] == ro: c[r['kind']].append(r['gap'])
      print(ro, {k: (len(v), round(sum(v)/3600, 1)) for k, v in c.items()})

if __name__ == '__main__':
    main()
