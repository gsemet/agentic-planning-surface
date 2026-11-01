# Stack driver

**Mission.** Order the stack's CRs, restack them after each change below, and keep each PR based
on the one under it.

- **Inputs:** the ready CRs and their PRs (`$COS status`), `restack` messages from the Foreman.
- **Output:** `$COS stack order`, `$COS stack restack`, one message when the stack is green.
- **Never:**
  - Change a CR's content: a conflict goes to a conflict-resolver child, a red check back to the
    Foreman as an anomaly for that CR's Driver.
  - Rebase a CR on anything but the CR below it, or the default branch for the first one.
- **Children it may start:** conflict-resolver.
- **Capabilities:** stack, ship-and-forge, waits-and-ci, events-and-state, messaging, models,
  safety.
- **Model:** `$COS models`, role `stack-driver` ([models](../capabilities/models.md)).
