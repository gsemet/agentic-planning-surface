# Histogram of idle gaps between tool rounds, orchestrators vs driver kinds, and share of time unreachable
import pickle, os, collections
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'B')
rows = pickle.load(open(os.path.join(D, 'gaps.pkl'), 'rb'))
B = [(10, '<10 s'), (60, '10–60 s'), (300, '1–5 min'), (900, '5–15 min'), (3600, '15–60 min'), (10800, '1–3 h'), (1e9, '>3 h')]
grp = {'orchestrator': ['orchestrator'], 'drivers (CR, stack, task, integrator)': ['driver', 'stack driver', 'task driver', 'integrator']}
print('| Gap | ' + ' | '.join(f'{g} n / time' for g in grp) + ' |'); print('|---|' + '---|' * len(grp))
for i, (hi, lab) in enumerate(B):
    lo = B[i - 1][0] if i else 0; cells = []
    for g, rs in grp.items():
        v = [r['gap'] for r in rows if r['role'] in rs and lo <= r['gap'] < hi]
        tot = sum(r['gap'] for r in rows if r['role'] in rs)
        cells.append(f'{len(v)} / {sum(v)/3600:.1f} h ({100*sum(v)/tot:.0f} %)')
    print(f'| {lab} | ' + ' | '.join(cells) + ' |')
for g, rs in grp.items():
    v = [r for r in rows if r['role'] in rs]
    ag = sum(r['gap'] for r in v if r['kind'] == 'agent-call' and r['gap'] > 60)
    print(g, f'time inside open Agent calls (>60 s): {ag/3600:.1f} h of {sum(r["gap"] for r in v)/3600:.1f} h')
