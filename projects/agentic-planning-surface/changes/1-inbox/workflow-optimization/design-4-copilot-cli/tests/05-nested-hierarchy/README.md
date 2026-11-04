# Series 05 — Nested hierarchy (aborted)

Goal: Foreman as an **independent** session, Drivers created without `relationship` so that they
nest in the Foreman session, `/every 3m heartbeat` on the Foreman, CoS deletes the Foreman at the
end. Kit: [kit/](./kit/) (still using the `factory.py` state CLI).

Outcome: stopped by the user a few minutes after start. The UI showed the expected hierarchy
(`[05 foreman]` with `[05 CR-1..3 driver]` nested under it). The CoS deleted the Foreman session.
No results were archived. The scenario was rerun without the state script as
[series 06](../06-nested-steered/README.md).
