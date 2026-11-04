import json,re,collections
rows=json.load(open('agents.json'))
byid={r['meta']['agent_id'].replace('agent-',''):r for r in rows}
def role(r):
    m=r['meta']
    if m.get('main'): return 'main (human-facing)'
    d=m.get('description','').lower()
    if 'orchestrator' in d: return 'orchestrator'
    if 'driver' in d: return 'driver'
    if re.search(r'review|critic|re-check|verify|audit', d): return 'reviewer/critic/audit'
    if re.search(r'coder|implement|fix |gap closer|add |update |writer', d): return 'coder/writer'
    if re.search(r'analyst|inventory|locator|research|explore|swrs ', d): return 'analyst/inventory'
    return 'other'
def stream(r):
    d=r['meta'].get('description','').lower()
    if r['meta'].get('main'): return 'main'
    # walk up parents to the top-level description
    p=r; seen=0
    while p['meta'].get('parentAgentId') and p['meta']['parentAgentId'] in byid and seen<5:
        p=byid[p['meta']['parentAgentId']]; seen+=1
    top=p['meta'].get('description','').lower()
    if re.search(r'swrs|analyst|inventory|locator|critic|gap closer|xc writer|okfreq|requirements|batch\d|reduction|shrink|p\d+(\.\d)? ', top+' '+d): return 'requirements baseline (CR 059/060)'
    if re.search(r'\bt\d+|fix plan|deep', top+' '+d): return 'deep-UX fix plan'
    if re.search(r'\bs\d+[ab]? (coder|reviewer)|driver cr .*s\d', top+' '+d): return 'CR 059 S-steps'
    if re.search(r'cr ?\d|orchestrator|stack|coder cr|reviewer cr|driver', top+' '+d): return 'CR pipeline (backlog → PR)'
    return 'other: '+top[:40]
agg=collections.defaultdict(lambda: collections.Counter())
for r in rows:
    k=role(r); t=r['tokens']
    a=agg[k]; a['n']+=1; a['cost']+=r['cost']; a['turns']+=r['turns']
    for kk in ('input_tokens','w5','w1h','cache_read_input_tokens','output_tokens'): a[kk]+=t.get(kk,0)
    a['result_chars']+=sum(r['result_chars'].values())
print('ROLE | n | cost | turns | cache_read | write5m | write1h | input | output | result MB')
tot=sum(a['cost'] for a in agg.values())
for k,a in sorted(agg.items(), key=lambda x:-x[1]['cost']):
    print(f"{k} | {a['n']} | {a['cost']:.2f} ({100*a['cost']/tot:.1f}%) | {a['turns']} | {a['cache_read_input_tokens']/1e6:.1f}M | {a['w5']/1e6:.2f}M | {a['w1h']/1e6:.2f}M | {a['input_tokens']/1e3:.0f}k | {a['output_tokens']/1e6:.2f}M | {a['result_chars']/1e6:.1f}")
s=collections.Counter(); sn=collections.Counter()
for r in rows: s[stream(r)]+=r['cost']; sn[stream(r)]+=1
print()
for k,v in s.most_common(): print(f"{v:8.2f} {sn[k]:4d} {k}")
