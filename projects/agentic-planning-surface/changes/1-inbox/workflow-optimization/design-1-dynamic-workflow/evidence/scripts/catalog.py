"""Per-agent and per-CR keyword matrix over handbacks and condensed transcripts of orchestrator-type agents."""
import json, re, os, glob, collections, sys
base = os.path.expanduser('~/.claude/projects/-Users-az02065-Projects-Nestor-agentic-coding-white-paper/dd375646-4450-4e52-a643-89ff1d9e405a/subagents/')
rows = {r['id']: r for r in json.load(open('agents.json'))}
CATS = {
 'ci_infra_rerun': r"dev-ci|\bhung\b|\bhang\b|cancel(?:l)?ed (?:it |the run )?and re-?ran|ETIMEDOUT|Ubuntu mirror|runner flake|infra(?:structure)? failure|as infra",
 'flaky_test': r"\bflak|intermittent|timing race|did not recur|passed on (?:the )?re-?run|test race|looks like (?:another )?timing",
 'rebase_conflict': r"conflict",
 'deps_node_modules': r"node_modules|shiki|npm ci|dependency-cruiser|--package-lock-only",
 'tool_env_drift': r"okfreq[^.]{0,80}(?:stale|lacks|old|newer|reorder|--check-links)|--check-links|stale okfreq|requirements-lint[^.]{0,60}fail",
 'permission_denial': r"denied|denial|classifier",
 'window_lock_or_screen': r"WINDOW-TESTS\.lock|screen (?:is |was )?locked|CGSSessionScreenIsLocked|locked screen|held WINDOW|lock was held|took the lock",
 'round_limit_hit': r"round limit|rounds are capped|capped at|grant (?:a )?(?:4th|fourth|5th|more|round)|no fourth|out of rounds|no rounds left|used (?:all|its) 3 rounds|has used its 3 rounds|round 3/3|blocked at round",
 'autonomous_decision': r"Autonomous decisions|Décisions prises en autonomie|Decisions made on my own|Decisions I made",
 'question_to_user': r"Question(?: for (?:the user|you|the main session))?:|Open question|Decision for (?:you|the main)|Needs your decision|Open decision",
 'forge_mechanics': r"mergeStateStatus|marked (?:old )?PR #?\d+ as merged|base cycle|closed #|cannot be edited|could not retarget|renaming a head branch",
 'process_deviation': r"Process deviation|review myself|instead of spawning|I started no coder|did the review myself|did not start a coder",
 'evidence_mismatch': r"before-shot matches user evidence: no|does not reproduce|not reproduced|did not reproduce|did not match",
 'stack_regression': r"regression the stack|stack itself introduced|introduced by #?\d+|relied on the old behaviour",
 'scope_split_or_merge': r"split (?:out|into)|separate (?:CR|PR)|follow-up CR|own PR|one PR, not a stack|out of scope|squash",
}
CR = re.compile(r'CR\s*0?(\d{2,3})|cr0?(\d{2,3})|Driver CR (\d+)')
def crs_of(desc):
    return sorted({int(next(g for g in m.groups() if g)) for m in CR.finditer(desc)})
agents = [r for r in rows.values() if r['first'] and r['last'] >= '2026-10-22' and re.search(r'orchestr|driver|integrat|stack|land|restart|resume|supervis|conflict|rebase|Fix ', r['desc'] or '', re.I)]
mat = {}
for r in agents:
    txt_hb = []; txt_all = []
    for line in open(base + r['id'] + '.jsonl'):
        d = json.loads(line)
        if d.get('type') != 'assistant': continue
        for b in d['message'].get('content', []):
            if b.get('type') == 'tool_use' and b['name'] == 'SubagentHandback': txt_hb.append(b['input'].get('message', ''))
            elif b.get('type') == 'text': txt_all.append(b['text'])
    t = '\n'.join(txt_hb + txt_all)
    hits = {k: len(re.findall(p, t, re.I)) for k, p in CATS.items()}
    # mechanical evidence: commands
    cmds = collections.Counter()
    for line in open(base + r['id'] + '.jsonl'):
        if '"tool_use"' not in line: continue
        d = json.loads(line)
        for b in d.get('message', {}).get('content', []) if d.get('type') == 'assistant' else []:
            if b.get('type') == 'tool_use' and b['name'] == 'Bash':
                c = b['input'].get('command', '')
                if re.search(r'gh run rerun', c): cmds['gh_run_rerun'] += 1
                if re.search(r'gh run cancel', c): cmds['gh_run_cancel'] += 1
                if re.search(r'gh workflow run', c): cmds['gh_workflow_run'] += 1
                if re.search(r'git rebase', c): cmds['git_rebase'] += 1
                if re.search(r'push[^\n]*--force-with-lease', c): cmds['force_push'] += 1
                if re.search(r'sleep \d+', c): cmds['sleep'] += 1
                if re.search(r'gh run watch|gh pr checks', c): cmds['ci_watch'] += 1
            if b.get('type') == 'tool_use' and b['name'] == 'Agent': cmds['spawn'] += 1
            if b.get('type') == 'tool_use' and b['name'] == 'SendMessage': cmds['sendmsg'] += 1
    mat[r['id']] = dict(desc=r['desc'], first=r['first'], depth=r['depth'], crs=crs_of(r['desc']), hits=hits, cmds=dict(cmds), nhb=len(txt_hb))
json.dump(mat, open('catalog_matrix.json', 'w'), indent=0)
# per-category: agents with >=1 hit, CRs touched
print(f"{len(agents)} agents")
for k in CATS:
    ag = [a for a in mat.values() if a['hits'][k]]
    crs = sorted({c for a in ag for c in a['crs']})
    print(f"{k:22s} agents {len(ag):3d} CRs {len(crs):3d}  {crs[:40]}")
tot = collections.Counter()
for a in mat.values(): tot.update(a['cmds'])
print(dict(tot))
