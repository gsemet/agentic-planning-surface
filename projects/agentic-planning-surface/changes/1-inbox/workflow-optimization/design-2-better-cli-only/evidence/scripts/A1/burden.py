import json, collections, re, sys
ev = json.load(open(sys.argv[1]))
START = sys.argv[2] if len(sys.argv) > 2 else '2026-10-22T16:00'
ev = [e for e in ev if e['ts'] >= START]
def primary(t):
    cats = t['cats']
    if not cats: return 'text-only'
    orch = [c for c in cats if c.startswith('orch')]
    if orch:
        for p in ('orch-launch', 'orch-relay', 'orch-script', 'orch-poll', 'orch-forge', 'orch-state'):
            if p in orch: return p
    if 'backlog' in cats: return 'backlog'
    if 'work-agent' in cats: return 'work-agent'
    return 'work-tool'
STATUS = re.compile(r"etat|état|on en est|^alors|comment ca se passe|o[uù] en es|where are you|que reste|status|converge|combien de temps|bloqu|0 agents|avancement|^\s*\?\s*$|tu es s[uû]r", re.I)
MERGE = re.compile(r"merg|c.est fait|^\s*done|^\s*doen|fix[ée]|both are merged", re.I)
CONT = re.compile(r"^\s*(continue|contineu|conitnue|reprend|finalise)", re.I)
def hkind(t):
    if CONT.search(t): return 'h-continue'
    if STATUS.search(t[:200]): return 'h-status'
    if MERGE.search(t[:120]) and len(t) < 200: return 'h-merged'
    return 'h-content'
# episodes
eps = []; cur = None
for e in ev:
    if e['type'] == 'input':
        k = e['kind'] if e['kind'] != 'human' else hkind(e['text'])
        cur = dict(trigger=k, ts=e['ts'], text=e['text'][:200], turns=[]); eps.append(cur)
    else:
        if cur is None: cur = dict(trigger='start', ts=e['ts'], text='', turns=[]); eps.append(cur)
        cur['turns'].append(e)
tc = collections.Counter(); tcost = collections.Counter()
for ep in eps:
    for t in ep['turns']:
        p = primary(t); tc[p] += 1; tcost[p] += t['cost']
tot = sum(tcost.values())
print('turns', sum(tc.values()), 'cost', round(tot, 2))
for k, v in tc.most_common(): print(f"  {k:12s} turns {v:5d}  ${tcost[k]:7.2f}  {100*tcost[k]/tot:5.1f}%")
# episode-level: trigger
ec = collections.Counter(); ecost = collections.Counter(); eturns = collections.Counter()
for ep in eps:
    ec[ep['trigger']] += 1; ecost[ep['trigger']] += sum(t['cost'] for t in ep['turns']); eturns[ep['trigger']] += len(ep['turns'])
print('episodes by trigger')
for k, v in ec.most_common(): print(f"  {k:18s} eps {v:4d} turns {eturns[k]:5d} ${ecost[k]:7.2f} {100*ecost[k]/tot:5.1f}%")
# episode classification: orchestration if >=50% of its cost in orch turns or triggered by machine input
def epclass(ep):
    if not ep['turns']: return 'empty'
    oc = sum(t['cost'] for t in ep['turns'] if primary(t).startswith('orch'))
    ac = sum(t['cost'] for t in ep['turns'])
    if ep['trigger'] in ('task-notification', 'agent-message'): return 'machine-relay' if oc / max(ac, 1e-9) < 0.5 else 'machine-orch'
    if ep['trigger'] in ('h-status', 'h-merged', 'h-continue'): return 'user-' + ep['trigger'][2:]
    return 'user-content-orch' if oc / max(ac, 1e-9) >= 0.5 else 'user-content-other'
cc = collections.Counter(); ccost = collections.Counter(); ct = collections.Counter()
for ep in eps:
    c = epclass(ep); cc[c] += 1; ccost[c] += sum(t['cost'] for t in ep['turns']); ct[c] += len(ep['turns'])
print('episodes by class')
for k, v in cc.most_common(): print(f"  {k:20s} eps {v:4d} turns {ct[k]:5d} ${ccost[k]:7.2f} {100*ccost[k]/tot:5.1f}%")
json.dump([dict(trigger=ep['trigger'], cls=epclass(ep), ts=ep['ts'], text=ep['text'], n=len(ep['turns']), cost=sum(t['cost'] for t in ep['turns']), prim=collections.Counter(primary(t) for t in ep['turns'])) for ep in eps], open('episodes.json', 'w'))
