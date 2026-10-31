# The production team

One card per role. A card holds only what a capable model would not do on its own from the
role's intent: the host's mechanics, who owns what, and the batch's invariants. General
engineering practice is left to the model.

| Role | Runs as | Owner | Card |
| --- | --- | --- | --- |
| Chief of Staff | the user's Desktop session | the user | [chief-of-staff](chief-of-staff.md) |
| Foreman | nested, detached Desktop session | Chief of Staff (starts it once) | [foreman](foreman.md) |
| CR Driver | `cr-driver` agent, background | Foreman | [cr-driver](cr-driver.md) |
| Stack driver | `stack-driver` agent, background | Foreman | [stack-driver](stack-driver.md) |
| QA driver | `qa-driver` agent, background | Foreman | [qa-driver](qa-driver.md) |
| Investigator | `investigator` agent, foreground | a Driver | [investigator](investigator.md) |
| Coder | `coder` agent, foreground | a Driver | [coder](coder.md) |
| Inspector | `inspector` agent, foreground | a Driver | [inspector](inspector.md) |
| Debugger | `debugger` agent, foreground | a Driver | [debugger](debugger.md) |
| Verifier | `verifier` agent, foreground | a Driver | [verifier](verifier.md) |
| Conflict resolver | `conflict-resolver` agent, foreground | a Driver or the stack driver | [conflict-resolver](conflict-resolver.md) |

## Model and effort

No role has a fixed model. Each agent file is written by `$COS setup` with
`model: <models.<role> in .agents/cos.json>`, `inherit` when unset. The Chief of Staff may set a
model per CR at the grill: it goes in the brief's **Models** line, and the Foreman or Driver
passes it as the `model` of that spawn. Nothing escalates on its own.

## Every card has

- **Mission**: one sentence.
- **Inputs** and **output**: what it reads, what it leaves behind, and where.
- **Never**: the non-obvious limits.
- **Capabilities**: the files of [../capabilities/](../capabilities/) it reads, and only those.
- **Model**: the placeholder. Fill it in `.agents/cos.json` or leave `inherit`.

The principles every role follows are in [../principles.md](../principles.md).
