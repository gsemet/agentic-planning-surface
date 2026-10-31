# cos production team: grill of 2026-10-31

> [!NOTE]
> Decisions on how the cos skill defines its production team. The reference was the poteto-mode skill (cursor/plugins, `pstack/skills/poteto-mode`): a `SKILL.md` that routes triggers to playbooks and to principle leaves. We do not import its playbooks for now.

## Decisions

| Topic | Decision |
| --- | --- |
| Structure | Roles plus playbooks. One card per role: mission, inputs, outputs, boundaries, model slot. The current capability files stay as the technical references the cards point to. |
| New roles | Debugger, independent Verifier, Investigator, Conflict resolver. They join Foreman, CR Driver, stack driver, QA driver, Coder and Inspector. |
| What to encode | Only what a 5.5 model would not do on its own from a clear intent. General engineering practice (reproduce first, smallest change, read before editing) is left out. |
| Situation playbooks | None written now. Feature, bug, red CI, conflict and QA-return playbooks describe what the model already does. A `playbooks/` folder with a placeholder README keeps room to import some later (poteto or others). |
| Following a playbook | Text only. No CLI step tracking. |
| Model choice | Not hard-coded. Each role card has a placeholder for model and effort, filled by the Chief of Staff at the grill or left to the default. No automatic escalation. |
| Principles | Short, cos-specific, non-obvious only: one line of rule, one line of why. |
| Rule evals | Later. The global scenario and the existing LLM cases stay. |

## What counts as non-obvious here

What the model cannot know from the intent, mostly:

- **Claude Desktop mechanics.**
  - A session started by a session cannot start sessions.
  - A message to a busy agent waits for its next tool round.
  - Background agents need `background: true` in their agent file, and agent files load at session start.
  - The 1-hour cache needs a wake before about 3300 s.
  - An undetached child sends one app note per turn.
- **Ownership across the team.**
  - Only the owner of a live agent may stop or message it.
  - A parent restarts a failing child and never does the child's work.
  - The Verifier never wrote the code it checks.
  - The Debugger hands over a proved diagnosis, not a patch.
- **Batch invariants.**
  - State changes only through `cos`.
  - A stale epoch stops at once.
  - A red check that is also red on main is not the CR's to fix.
  - Never merge.
  - Never fall back to another design when preflight fails.
