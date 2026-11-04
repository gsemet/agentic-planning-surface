# Main-session actions that belong to a factory child (orchestrator/driver/stack driver) since 10-22 16:00:
# TaskStop, re-brief/restart spawns, and mechanical child work done by main (git rebase/commit/push/merge,
# gh pr merge/ready/edit, heavy CI dispatch, gh run rerun, gh stack, worktree removal).
import json, os, re, collections, pickle
P = os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a.jsonl')
START = '2026-10-22T16:00'
PAT = [('merge-pr', r'gh pr merge'), ('rebase', r'git (-C \S+ )?rebase'), ('push', r'git (-C \S+ )?push'), ('commit', r'git (-C \S+ )?commit'),
       ('heavy-ci', r'gh workflow run'), ('ci-rerun', r'gh run (rerun|cancel)'), ('stack', r'gh stack'), ('pr-edit', r'gh pr (ready|edit|create)'),
       ('worktree-rm', r'git (-C \S+ )?worktree remove|git (-C \S+ )?branch -D|push origin --delete'), ('ci-watch', r'gh run watch|gh pr checks .*--watch|sleep \d{3,}')]
ev = []; res = {}
for line in open(P):
    if '"tool_use"' not in line and '"tool_result"' not in line: continue
    try: x = json.loads(line)
    except Exception: continue
    ts = x.get('timestamp', '')
    if ts < START: continue
    m = x.get('message') or {}; c = m.get('content')
    if not isinstance(c, list): continue
    for z in c:
        if z.get('type') == 'tool_use':
            n = z['name']; i = z.get('input') or {}
            if n == 'TaskStop': ev.append((ts, 'TaskStop', str(i)[:120], z['id']))
            elif n in ('Agent', 'Task'):
                d = i.get('description', '')
                if re.search(r'orchestrat|driver|integrator', d, re.I): ev.append((ts, 'spawn', d, z['id']))
            elif n == 'Bash':
                cmd = i.get('command', '')
                for k, rx in PAT:
                    if re.search(rx, cmd): ev.append((ts, k, (i.get('description') or '')[:70] + ' :: ' + cmd[:110].replace('\n', ' '), z['id'])); break
        elif z.get('type') == 'tool_result':
            cc = z.get('content'); cc = ' '.join(q.get('text', '') for q in cc if isinstance(q, dict)) if isinstance(cc, list) else str(cc)
            if re.search(r'denied|classifier', cc[:400], re.I): res[z.get('tool_use_id')] = cc[:200]
cnt = collections.Counter(e[1] for e in ev)
print(cnt)
pickle.dump((ev, res), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'B', 'takeovers.pkl'), 'wb'))
for e in ev:
    if e[1] in ('ci-watch',): continue
    print(e[0][5:16], e[1], '|', e[2][:150], '| DENIED: ' + res[e[3]][:100] if e[3] in res else '')
