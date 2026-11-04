import pickle,re,collections,json
rows=pickle.load(open('../facrows.pkl','rb'))
R=[
 ('L_report', lambda r: r['fid']=='agent-main' or (r['src']!='MAIN' and re.search(r'Orchestrator|orchestrat',r['dstn']) and not re.search(r'Orchestrator|orchestrat',r['srcn']))),
 ('G_restart', lambda r: re.search(r'rate limit|Resume K|Resume L|Resume:|Resume CR|Nudge|stale|Stale header|cut off by a session limit|Resume T1|resume',r['summary']+' '+r['msg'][:200],re.I) and not re.search(r'round 4|round 5',r['summary'])),
 ('E_machine', lambda r: re.search(r'PAUSE|caffeinate|shut',r['summary']+r['msg'][:100])),
 ('F_unblock', lambda r: re.search(r'authoriz|denial|cannot unlock|without rewrite|screen is locked',r['summary']+r['msg'][:300],re.I)),
 ('A_info', lambda r: re.search(r'status ping|request status|FYI|For information|Latest CI|Relay .* done|Tell K that|landed on main|wt-059 now',r['summary']+' '+r['msg'][:120],re.I)),
 ('D2_stack_shape', lambda r: re.search(r'Reorder|top|cycle|Add CRs 122|on the CR 135 stack|Move 123|Restack|outside|append|Fix goes on top',r['summary'],re.I)),
 ('D1_merge_rebase_land', lambda r: re.search(r'merged|Merges|rebase|Rebase|land',r['summary'],re.I)),
 ('B_add_remove', lambda r: re.search(r'Add CR|New CR|add a 4th|Night plan|Night batch|dropped|After landing 132|start next batch|Extend K|belong to orchestrator|stand down|focus 056|Add skipped|Parallelize|Overnight goal|start its driver',r['summary']+' '+r['msg'][:100],re.I)),
 ('C_scope', lambda r: re.search(r'decision|scope|user adds|README link|Page structure|list-table|handles outside|Known issue|follow-up fixes|real reproduction|max 8 commits|rounds|Grant|round 4|round 5|Opus|Final shape|one squashed|wide scrolling|Before-shot|missing review|Re-check batch',r['summary']+' '+r['msg'][:150],re.I) and r['src']=='MAIN' or re.search(r'User change|Scope extension|User decision|user explicitly|round 4|round 5|Round limit',r['summary']+' '+r['msg'][:120])),
 ('I_rule', lambda r: re.search(r'Rule|rule|English|trailer|naming|format|INDEX.md|brief moved|Brief moved|folder layout|renamed|Deliverables|deliverable|ready, not draft|Refresh ORCHESTRATOR|bypass|Adopt new|prefix',r['summary']+' '+r['msg'][:100])),
 ('H_ci', lambda r: re.search(r'heavy|CI|flaky|regression|Bisect|hang',r['summary'],re.I)),
 ('K_round', lambda r: r['src']!='MAIN'),
]
cats=collections.OrderedDict()
for r in rows:
    c='Z_other'
    for name,f in R:
        try:
            if f(r): c=name;break
        except Exception as e: pass
    r['cat']=c
over=json.load(open('../overrides.json')) if __import__('os').path.exists('../overrides.json') else {}
for r in rows:
    if str(r['n']) in over: r['cat']=over[str(r['n'])]
    elif r['src']=='MAIN': r['cat']='UNSET'
    elif r['fid']=='agent-main' or not __import__('re').search(r'rchestr|[Dd]river',r['srcn']): r['cat']='L_report_back'
    else: r['cat']='K_round_dispatch'
pickle.dump(rows,open('../facrows.pkl','wb'))
import sys
if len(sys.argv)>1:
    for r in rows:
        print(r['n'],r['cat'],'|',r['srcn'][:18],'->',r['dstn'][:22],'|',r['summary'][:70])
c=collections.Counter((r['cat'],'M' if r['src']=='MAIN' else 'a') for r in rows)
for k in sorted(c): print(k,c[k])
