"""Condense a Claude Code jsonl transcript into a readable text: one line per event."""
import json, sys
def s(x, n):
    x = x if isinstance(x, str) else json.dumps(x)
    x = x.replace('\n', ' \\n ')
    return x[:n] + ('...' if len(x) > n else '')
def condense(path, out, tn=1500, rn=600):
    with open(path) as f, open(out, 'w') as o:
        for line in f:
            try: d = json.loads(line)
            except Exception: continue
            t = d.get('type'); ts = (d.get('timestamp') or '')[:19]
            msg = d.get('message') or {}
            c = msg.get('content') if isinstance(msg, dict) else None
            if t == 'assistant' and isinstance(c, list):
                for b in c:
                    if b.get('type') == 'text' and b['text'].strip():
                        o.write(f"{ts} A-TEXT: {s(b['text'], tn)}\n")
                    elif b.get('type') == 'tool_use':
                        inp = b.get('input', {})
                        if b['name'] == 'Bash': v = inp.get('command', '')
                        elif b['name'] in ('Agent', 'Task'): v = f"[{inp.get('description')}] model={inp.get('model')} bg={inp.get('run_in_background')} :: {inp.get('prompt','')}"
                        elif b['name'] == 'SendMessage': v = inp
                        elif b['name'] in ('Read', 'Write', 'Edit'): v = inp.get('file_path', '') + (' :: ' + s(inp.get('content', inp.get('new_string', '')), 300) if b['name'] != 'Read' else '')
                        else: v = inp
                        o.write(f"{ts} TOOL {b['name']}: {s(v, 700)}\n")
            elif t == 'user':
                if isinstance(c, str):
                    o.write(f"{ts} USER: {s(c, tn)}\n")
                elif isinstance(c, list):
                    for b in c:
                        if b.get('type') == 'tool_result':
                            cc = b.get('content')
                            if isinstance(cc, list): cc = ' '.join(x.get('text', '') for x in cc if isinstance(x, dict))
                            tag = 'RESULT-ERR' if b.get('is_error') else 'RESULT'
                            o.write(f"{ts} {tag}: {s(cc or '', rn)}\n")
                        elif b.get('type') == 'text':
                            o.write(f"{ts} USER: {s(b['text'], tn)}\n")
            elif t == 'attachment' and (d.get('attachment') or {}).get('type') == 'queued_command':
                a = d['attachment']; o_ = a.get('origin') or {}
                pr = a.get('prompt'); pr = pr if isinstance(pr, str) else ' '.join(x.get('text', '') for x in (pr or []) if isinstance(x, dict))
                kind = o_.get('kind'); frm = o_.get('from', '')
                o.write(f"{ts} MSG[{kind}{(':'+frm) if frm else ''}]: {s(pr, tn)}\n")
            elif t == 'system':
                o.write(f"{ts} SYSTEM: {s(d.get('content') or d.get('subtype') or '', 300)}\n")
if __name__ == '__main__':
    condense(sys.argv[1], sys.argv[2], *(int(a) for a in sys.argv[3:]))
