import re, sys, os, glob
S, R = sys.argv[1], sys.argv[2]
DATA = {"D1": f'"{S}/research/data/agents.jsonl"', "A1": f'"{S}/research2/scripts/data/agents.jsonl"',
        "A2": f'os.environ.get("A2DATA", "{S}/research2/data/A2/agents.jsonl")'}
HELP = '''
# research3 correction: Sonnet 5.5 cache read is $0.10/MTok (0.05x base input), not $0.20.
# Haiku 5.5 uses the >100k-prompt tier (prompt = input + cache read + cache writes) for the whole request.
HAIKU_HI = (0.50, 0.625, 1.0, 0.05, 2.50)
def PT(t, fam=None, prompt=None):
    f = fam or t["fam"]
    if f == "haiku":
        pr = prompt if prompt is not None else t["in"] + t["cr"] + t["w5"] + t["w1h"]
        if pr > 100000: return HAIKU_HI
    return PRICE[f]
def turn_billed(t):
    p = PT(t); return (t["in"] * p[0] + t["w5"] * p[1] + t["w1h"] * p[2] + t["cr"] * p[3] + t["out"] * p[4]) / 1e6
'''
def sub(path, old, new, count=1, must=True):
    s = open(path).read()
    if old not in s:
        if must: raise SystemExit(f"MISSING in {path}: {old!r}")
        return
    s = s.replace(old, new) if count == 0 else s.replace(old, new, count)
    open(path, "w").write(s)
for d in ("D1", "A1", "A2"):
    c = f"{R}/{d}/common.py"
    s = open(c).read()
    s = s.replace('"sonnet": (2.0, 2.5, 4.0, 0.20, 10.0)', '"sonnet": (2.0, 2.5, 4.0, 0.10, 10.0)')
    s = re.sub(r'^DATA = .*$', 'DATA = ' + DATA[d], s, count=1, flags=re.M)
    s = s.replace("BYID = {}\n", "BYID = {}\n" + HELP, 1)
    s = s.replace('    for r in rows:\n        r["cost"] = sum(t["cost"] for t in r["turns"])',
                  '    for r in rows:\n        for t in r["turns"]: t["cost"] = turn_billed(t)\n        r["cost"] = sum(t["cost"] for t in r["turns"])', 1)
    assert "turn_billed(t)\n" in s and "0.10, 10.0" in s and "HAIKU_HI" in s
    open(c, "w").write(s)
    for f in glob.glob(f"{R}/{d}/*.py"):
        s = open(f).read(); s0 = s
        s = s.replace('PRICE[t["fam"]]', 'PT(t)').replace('PRICE[T[k]["fam"]]', 'PT(T[k])')
        s = s.replace('PRICE[fam or t["fam"]]', 'PT(t, fam)')
        # other copies of the flat price table (unused by the reports, but keep them consistent)
        s = re.sub(r"(['\"]sonnet['\"]:\s*\(2\.0,\s*2\.5,\s*4\.0,\s*)0\.20", r"\g<1>0.10", s)
        s = s.replace('"sonnet":(2.0,2.5,4.0,0.20,10.0)', '"sonnet":(2.0,2.5,4.0,0.10,10.0)')
        if s != s0: open(f, "w").write(s)
# D1 file paths
sub(f"{R}/D1/b_runs.py", 'os.path.join(HERE, "..", "data", "prs.json")', f'"{S}/research/data/prs.json"')
sub(f"{R}/D1/b_runs.py", 'os.path.join(HERE, "..", "data", "runs.json")', 'os.path.join(HERE, "runs.json")')
sub(f"{R}/D1/i_percr.py", 'os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "runs.json")', 'os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs.json")')
# A2: Haiku tier now inside tcost via PT -> drop the manual x5
sub(f"{R}/A2/wcommon.py", 'p = PT(t, fam)\n    w = t["w5"]', 'p = PT(t, fam)\n    w = t["w5"]', must=True)
sub(f"{R}/A2/a2_models.py", 'tcost(t, "haiku") * (5 if ctx(t) > 100000 else 1)', 'tcost(t, "haiku")')
# A2 hard-coded Sonnet driver-event price
sub(f"{R}/A2/a2_options.py", 'DRV_EVENT = (DCTX * (2.5 - 0.2) + 2 * DCTX * 0.2 + 2 * 400 * 10) / 1e6',
    'DRV_EVENT = (DCTX * (2.5 - 0.1) + 2 * DCTX * 0.1 + 2 * 400 * 10) / 1e6')
# A1 simulator: Haiku tier on the simulated prompt size
sub(f"{R}/A1/a1_sim.py", '        S = max(B * 0.5, ctx(t) - removed)\n',
    '        S = max(B * 0.5, ctx(t) - removed)\n        if f == "haiku":\n            p = PT(t, "haiku", S); wprice = p[2] if ttl > 300 else p[1]\n')
print("ok")
