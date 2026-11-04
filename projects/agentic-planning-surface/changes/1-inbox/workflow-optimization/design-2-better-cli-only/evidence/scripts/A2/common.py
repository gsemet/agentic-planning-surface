import json, re, os, datetime, collections
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("A2DATA", os.path.join(HERE, "..", "..", "data", "A2", "agents.jsonl"))
PRICE = {"opus": (4.0, 5.0, 8.0, 0.20, 20.0), "sonnet": (2.0, 2.5, 4.0, 0.20, 10.0),
         "haiku": (0.10, 0.125, 0.20, 0.01, 0.50), "fable": (10.0, 12.5, 20.0, 0.25, 50.0)}
BYID = {}
RUN_ROOTS = {"a7dc8322f1d2b1eb9": "run1", "afeef650ccb1e205e": "run1", "a71ba715a962d0a53": "run2",
             "a21e1ec0a8fc37d31": "run3", "a725410a2169211f8": "run5"}
ROLES = ["main", "orchestrator", "driver", "stack driver", "task driver", "integrator",
         "coder/writer", "reviewer", "analyst", "other"]

def ts(s): return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))

def load():
    rows = [json.loads(l) for l in open(DATA)]
    byid = {r["meta"]["agent_id"]: r for r in rows}
    global BYID; BYID = byid
    for r in rows:
        r["cost"] = sum(t["cost"] for t in r["turns"])
        r["desc"] = r["meta"].get("description", "") if not r["meta"].get("main") else "MAIN " + r["meta"]["session"][:8]
        r["role"] = role(r)
    for r in rows:
        chain = []; p = r; seen = 0
        while p["meta"].get("parentAgentId") and p["meta"]["parentAgentId"] in byid and seen < 6:
            p = byid[p["meta"]["parentAgentId"]]; chain.append(p["meta"]["agent_id"]); seen += 1
        r["ancestors"] = chain
        r["top"] = p
    for r in rows:
        r["run"] = run_of(r)
        r["ws"] = workstream(r)
    return rows, byid

def role(r):
    m = r["meta"]
    if m.get("main"): return "main"
    d = m.get("description", "").lower()
    if "orchestrat" in d or re.match(r"land cr \d+", d): return "orchestrator"
    if "stack driver" in d: return "stack driver"
    if "integrator" in d: return "integrator"
    if re.search(r"task driver|cr \d+ t\d+ driver", d): return "task driver"
    if "driver" in d: return "driver"
    if re.search(r"review|critic|re-check|recheck|verify|evidence check", d): return "reviewer"
    if re.search(r"coder|implement|fix|gap closer|^add |update |writer|revise|resolve|follow-up|repair|port |write |finish|shrink|swrs|strs", d): return "coder/writer"
    if re.search(r"analyst|inventory|locator|research|investigation|analysis|study|measurements|reproduce|audit|performance|feasibility|recorder|plan critical", d): return "analyst"
    return "other"

def cr_of(desc):
    m = re.search(r"\bcr ?(\d{3})\b", desc.lower()) or re.search(r"\bcr\w* driver (\d{3})\b", desc.lower())
    return m.group(1) if m else None

def run_of(r):
    ids = [r["meta"]["agent_id"]] + r["ancestors"]
    root = next((RUN_ROOTS[i] for i in ids if i in RUN_ROOTS), None)
    if root is None: return None
    if root in ("run3", "run5"):
        rootid = "a21e1ec0a8fc37d31" if root == "run3" else "a725410a2169211f8"
        if r["meta"]["agent_id"] == rootid: return "run3" if root == "run3" else "run4/5"
        chain = [r] + [None]
        # the direct child of the root orchestrator decides
        lvl = r
        for a in [r["meta"]["agent_id"]] + r["ancestors"]:
            pass
        d = r["desc"].lower()
        # walk ancestors to the one whose parent is the root
        cur = r; anc = r["ancestors"]
        names = [r["desc"]] + [BYID[a]["desc"] for a in anc if a in BYID]
        idx = anc.index(rootid) if rootid in anc else -1
        drv = names[idx] if idx >= 0 else r["desc"]
        drv = drv.lower()
        if "135" in drv: return "run4/5"
        if re.search(r"13[2-4]", drv): return "run3"
        return "run4/5"
    return root

def workstream(r):
    if r["meta"].get("main"):
        return "main session" if "agentic-coding-white-paper" in r["meta"]["project"] else "other project (main)"
    if "agentic-coding-white-paper" not in r["meta"]["project"]: return "other project"
    if r["run"]: return "CR factory " + r["run"]
    top = r["top"]["meta"].get("description", "").lower(); d = r["meta"].get("description", "").lower()
    s = top + " | " + d
    if top.startswith("orchestrator p1+p2"): return "CR pipeline before run 1"
    if re.search(r"swrs|strs|analyst|inventory|locator|critic|gap closer|xc writer|okfreq|requirements batch|reduction|shrink|re-check|recheck|revise|orchestrator [fghijkl]\b|evidence check|completeness audit|e2e campaign", s): return "requirements base (CR 059/060)"
    if re.search(r"\bs\d+[ab]? (coder|reviewer)|cr 056|orchestrator d:", s): return "CR 056 refactor"
    if re.search(r"\bt\d+ |\bp\d+ |deep|fix plan", top): return "deep-UX fix plan"
    if re.search(r"fable|security threat|performance review|modularity|supply chain|page-side|memory-leak|performance measurements|render pipeline", s): return "audit research"
    if re.search(r"cr ?\d|orchestrat|stack|driver|coder|reviewer|rebase", s): return "CR pipeline before run 1"
    return "other: " + top[:40]

def strip_cmd(cmd):
    c = cmd.strip()
    for _ in range(6):
        c0 = c
        c = re.sub(r"^\(?\s*(set [^;&]+|cd [^&;]+|export [^;&]+|unset [^;&]+|[A-Za-z_]+=(\"[^\"]*\"|'[^']*'|\S+)( [A-Za-z_]+=\S+)*)\s*(&&|;|\n)\s*", "", c)
        c = re.sub(r"^((env (-u \S+ )*)|([A-Z_]+=\S+ ))+", "", c)
        c = re.sub(r"^(rtk (proxy )?|timeout \d+\w? |time |fnm exec( --using=\S+)? (-- )?|caffeinate -\w+ (-t \d+ )?|\\\\?)", "", c)
        c = re.sub(r"^\\", "", c)
        m = re.match(r"^for [^;]+;\s*do\s+(.*)", c, re.S)
        if m: c = m.group(1)
        if c == c0: break
    return c

RUNNER = r"^\(?\s*(just|npm|npx|node|xvfb-run|caffeinate[^;&|]*?|sh|zsh|bash|make|uv run|pytest|\.?/?\S*\.sh)\b"
def bash_kind(cmd):
    c = strip_cmd(cmd)
    if re.search(r"\bsleep\b", c) and re.search(r"gh (run|pr)|until|while|for ", c): return "poll"
    if re.search(r"wait\.sh|--watch|gh run watch", c): return "poll"
    if re.search(r"(hv|vs|ui)\.sh|vscode-ui|screencapture|ioreg", c): return "ui-drive"
    if re.search(r"gate\.sh|finish\.sh", c): return "gate-long"
    if re.match(r"^(cat|head|tail|sed -n|sed -E -n|grep|egrep|/usr/bin/grep|rg|ls|find|wc|awk|jq|diff|stat|file |tree|du |cut |nl |show\(\)|n\(\)|f=\$\()", c) and not re.search(r"(^|[^2])>\s*[^&/]|>\|", c.split("|")[0]):
        return "read-shell"
    if re.match(r"^git ", c):
        if re.match(r"^git (status|log|diff|show|branch|rev-parse|fetch|ls-remote|merge-base|rev-list|remote|cat-file|for-each-ref|describe|blame|ls-files|grep)", c): return "git-read"
        if re.match(r"^git worktree", c): return "git-worktree"
        return "git-write"
    if re.match(r"^gh (run|pr checks|workflow)", c): return "gh-ci"
    if re.match(r"^gh stack", c): return "gh-stack"
    if re.match(r"^gh pr (create|edit|ready|comment)", c): return "gh-pr-write"
    if re.match(r"^gh ", c): return "gh-read"
    if re.match(RUNNER, c) or re.match(r"^\(?just", c):
        if re.search(r"preflight|test:integration|test:stress|test:e2e|test:window|integration|playwright|just ci|stress|window|xvfb|visual|test:all|e2e", c): return "gate-long"
        if re.search(r"just (check|lint|test|typecheck|requirements|fmt)|npm (run )?(test|lint|typecheck|test:unit|build|compile|run)|npx (tsc|vitest|eslint|mocha|prettier)|tsc|unit|mocha|vitest", c): return "gate-fast"
    if re.search(r"okfreq|requirements-", c): return "okfreq"
    if re.match(r"^sleep", c): return "sleep"
    if re.search(r"<<\s*'?EOF|>\s*\S+\.(md|json|txt|ya?ml|ts|py|sh)|>\|\s*\S+|sed -i|tee |perl -pi|\\?(cp|mv) ", c): return "write-shell"
    if re.match(r"^(npm|npx|node|fnm)", c): return "node"
    if re.match(r"^(uv|python3?|pytest|\$O|\$STUDIO_OKFREQ)", c): return "python"
    if re.match(r"^(pgrep|caffeinate|nohup|kill|pkill|ps |lsof|date|echo|printf|test |\[|mkdir|rm|ln |touch|curl|open |source|command|which|if |\{|perl)", c): return "sys"
    return "other"

MECH_BASH = {"git-read", "git-write", "git-worktree", "gh-ci", "gh-stack", "gh-pr-write", "gh-read", "poll", "sleep",
             "read-shell", "write-shell", "sys", "gate-long", "gate-fast", "okfreq", "python", "node", "other"}
STATUS_FILE = re.compile(r"STATE\.md|ORCHESTRATOR|STACK-STATE|TASKS\.md|RUN-BRIEF|PR-BODY|report\.md|\.lock", re.I)

def tool_kind(t):
    name, short = t[0], t[1]
    if name == "Bash": return "bash:" + bash_kind(short)
    if name in ("Edit", "Write"): return ("edit-status" if STATUS_FILE.search(short) else "edit-src" if re.search(r"/(src|test)/", short) else "edit-other")
    if name == "Read": return "read-status" if STATUS_FILE.search(short) else "read"
    if name in ("Agent", "Task"): return "spawn"
    if name == "SendMessage": return "sendmessage"
    if name in ("TaskOutput", "BashOutput", "Monitor", "TaskStop", "KillShell"): return "wait-tool"
    if name in ("Grep", "Glob"): return "read"
    if name == "ScheduleWakeup": return "wait-tool"
    return "tool:" + name

def rebuild(t, i):
    ctx = t["in"] + t["cr"] + t["w5"] + t["w1h"]; w = t["w5"] + t["w1h"]
    return i > 0 and ctx > 20000 and w > 0.6 * ctx

def ctx(t): return t["in"] + t["cr"] + t["w5"] + t["w1h"]

def write_price(t):
    p = PRICE[t["fam"]]; return (t["w5"] * p[1] + t["w1h"] * p[2]) / 1e6

def gap(turns, i):
    if i == 0: return None
    return (ts(turns[i]["ts"]) - ts(turns[i - 1]["ts_last"])).total_seconds()

def trig(t):
    ks = [x[0] for x in t["inputs"]]
    for k in ("steer", "handback", "peer_msg", "task_notif", "compact", "compact_summary", "tool_result", "system"):
        if k in ks: return k
    return "none"
