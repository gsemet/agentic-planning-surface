# Message formats

One line each, prefixed by `[sender→receiver]`. Links are full URLs. This file is the only
definition; capability files point here.

## Chief of Staff → Foreman

Print the line with `$COS order …`; it carries the order id the Foreman needs.

```text
[cos→foreman] order O-<k> add <title> | order O-<k> drop <cr> | order O-<k> first <cr>
[cos→foreman] order O-<k> change <cr> <text> | order O-<k> merged <cr>
[cos→foreman] order O-<k> pause | order O-<k> resume
[cos→foreman] answer <cr> <text> | ping
```

## Foreman → Chief of Staff

```text
[foreman→cos] ready <batch>
[foreman→cos] ok O-<k> <what>
[foreman→cos] ask question <cr> <text> | ask blocked <cr> <reason> | ask refused <cr> <exact text>
[foreman→cos] ask ready <cr> <pr-link> | ask stack-ready <cr>=<link>… | ask budget <spent>/<budget>
[foreman→cos] pong <status line>
[foreman→cos] final <report path>
```

## Foreman → Driver

```text
[foreman→driver <cr>] round <note> | change <text> | first: you are top priority | answer <text>
[foreman→driver <cr>] ping: reply with your state
[foreman→stack] restack
```

## Driver → Foreman

```text
[driver <cr>→foreman] hand-back ready <pr-link> | hand-back blocked <reason>
[driver <cr>→foreman] question <text> | anomaly <text>
[qa <cr>→foreman] anomaly <cr> <finding> | qa done <cr> <n> findings
[stack→foreman] hand-back ready <links> | anomaly <cr> <text>
```

## Driver → its foreground child

The spawn prompt, not a message: the CR id, the batch, the worktree path, the round number, the
task, the previous round note, and the findings to address.
