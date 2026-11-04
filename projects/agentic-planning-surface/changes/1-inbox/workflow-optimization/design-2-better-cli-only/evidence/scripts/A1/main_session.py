"""Stream the main session and emit per-turn (dedup by message.id) records with cost and classification."""
import json, re, sys, os
SRC = os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a.jsonl')
START, END = sys.argv[1], sys.argv[2]
OUT = sys.argv[3]
PRICE = {  # input, 5m write, 1h write, cache read, output  ($/MTok)
    'opus': (4.0, 5.0, 8.0, 0.20, 20.0), 'sonnet': (2.0, 2.5, 4.0, 0.20, 10.0),
    'haiku': (0.10, 0.125, 0.20, 0.01, 0.50), 'fable': (4.0, 5.0, 8.0, 0.20, 20.0)}
def fam(m):
    for k in PRICE:
        if k in (m or ''): return k
    return 'opus'
def cost(u, m):
    p = PRICE[fam(m)]
    cc = u.get('cache_creation') or {}
    w5 = cc.get('ephemeral_5m_input_tokens', 0) or 0
    w1 = cc.get('ephemeral_1h_input_tokens', 0) or 0
    if not cc: w5 = u.get('cache_creation_input_tokens', 0) or 0
    return (u.get('input_tokens', 0) * p[0] + w5 * p[1] + w1 * p[2] + u.get('cache_read_input_tokens', 0) * p[3]
            + u.get('output_tokens', 0) * p[4]) / 1e6
ORCH_AGENT = re.compile(r'orchestr|driver|stack|integrat|land|restart|resume|supervis|rebase', re.I)
STATEF = re.compile(r'ORCHESTRATOR|STATE\.md|STACK-STATE|TASKS\.md|RUN-BRIEF|03-requests|changes/requests|WINDOW-TESTS|04-archives|archives/', re.I)
FORGE = re.compile(r'\bgh (pr|run|stack|workflow|api)|git (worktree|branch -D|branch -d|push|rebase|fetch|merge|reset)|caffeinate', re.I)
POLL = re.compile(r'\bsleep \d|until |while ', re.I)
def classify(tools):
    cats = []
    for name, inp in tools:
        s = json.dumps(inp)
        if name in ('Agent', 'Task'):
            cats.append('orch-launch' if ORCH_AGENT.search(inp.get('description', '') or '') else 'work-agent')
        elif name in ('SendMessage', 'TaskStop'):
            cats.append('orch-relay')
        elif name in ('Monitor', 'TaskOutput'):
            cats.append('orch-poll')
        elif name in ('Write', 'Edit'):
            fp = inp.get('file_path', '')
            c = inp.get('content', '') or inp.get('new_string', '')
            if fp.endswith('.py') and re.search(r'STATE\.md|task\.md|rules\.md|worktree', c): cats.append('orch-script')
            elif STATEF.search(fp) and '02-backlog' not in fp: cats.append('orch-state')
            elif '02-backlog' in fp or '01-inbox' in fp: cats.append('backlog')
            else: cats.append('work-edit')
        elif name == 'Read':
            fp = inp.get('file_path', '')
            if STATEF.search(fp): cats.append('orch-state')
            elif '02-backlog' in fp or '01-inbox' in fp: cats.append('backlog')
            else: cats.append('work-read')
        elif name == 'Bash':
            cmd = inp.get('command', '')
            if re.search(r'python3?[^\n]*<<', cmd) and re.search(r'task\.md|rules\.md|STATE\.md', cmd) and 'mkdir' in cmd: cats.append('orch-script')
            elif POLL.search(cmd) and (FORGE.search(cmd) or STATEF.search(cmd)): cats.append('orch-poll')
            elif FORGE.search(cmd): cats.append('orch-forge')
            elif STATEF.search(cmd): cats.append('orch-state')
            elif '02-backlog' in cmd or '01-inbox' in cmd: cats.append('backlog')
            else: cats.append('work-bash')
        else:
            cats.append('other-tool:' + name)
    return cats
def input_kind(text):
    t = text.lstrip()
    if t.startswith('<task-notification>'): return 'task-notification'
    if t.startswith('Another Claude session sent a message') or t.startswith('<agent-message') or t.startswith('<cross-session-message'): return 'agent-message'
    if t.startswith('This session is being continued'): return 'compact'
    if t.startswith('<local-command') or t.startswith('<command-name>'): return 'command'
    if t.startswith('<system-reminder>') or t.startswith('Caveat:'): return 'system'
    return 'human'
msgs = {}; order = []; inputs = []
for line in open(SRC):
    d = json.loads(line)
    ts = d.get('timestamp', '')
    if not (START <= ts < END) or d.get('isSidechain'): continue
    t = d.get('type')
    if t == 'assistant':
        m = d['message']; mid = m.get('id')
        if m.get('model') == '<synthetic>': continue
        if mid not in msgs:
            msgs[mid] = dict(id=mid, ts=ts, model=m.get('model'), usage=m.get('usage', {}), tools=[], text='')
            order.append(('A', mid))
        r = msgs[mid]; r['usage'] = m.get('usage', r['usage'])
        for b in m.get('content', []):
            if b.get('type') == 'tool_use':
                if b.get('id') in r.setdefault('tids', set()): continue
                r['tids'].add(b.get('id')); r['tools'].append((b['name'], b.get('input', {})))
            elif b.get('type') == 'text' and b['text'] not in r['text']: r['text'] += b['text']
    elif t == 'user' and not d.get('isMeta'):
        c = d['message']['content']
        if isinstance(c, str): text = c
        else:
            if any(b.get('type') == 'tool_result' for b in c): continue
            text = ' '.join(b.get('text', '') for b in c if b.get('type') == 'text')
            if any(b.get('type') == 'image' for b in c): text = '[image] ' + text
        k = 'compact' if d.get('isCompactSummary') else input_kind(text)
        inputs.append(dict(ts=ts, kind=k, text=text[:3000])); order.append(('I', len(inputs) - 1))
    elif t == 'user' and d.get('isMeta'):
        c = d['message']['content']
        text = c if isinstance(c, str) else ' '.join(b.get('text', '') for b in c if isinstance(b, dict))
        if 'agent-message' in text[:200] or 'Another Claude session' in text[:60]:
            inputs.append(dict(ts=ts, kind='agent-message', text=text[:3000])); order.append(('I', len(inputs) - 1))
out = []
for kind, ref in order:
    if kind == 'I': out.append(dict(type='input', **inputs[ref]))
    else:
        r = msgs[ref]
        out.append(dict(type='turn', ts=r['ts'], id=r['id'], model=r['model'], cost=cost(r['usage'], r['model']),
                        ctx=(r['usage'].get('input_tokens', 0) + r['usage'].get('cache_read_input_tokens', 0) + r['usage'].get('cache_creation_input_tokens', 0)),
                        out=r['usage'].get('output_tokens', 0), cats=classify(r['tools']),
                        tools=[(n, (i.get('description') or i.get('command') or i.get('file_path') or json.dumps(i))[:300]) for n, i in r['tools']],
                        text=r['text'][:600]))
json.dump(out, open(OUT, 'w'))
print(len(msgs), 'turns', len(inputs), 'inputs', round(sum(cost(m['usage'], m['model']) for m in msgs.values()), 2), '$')
