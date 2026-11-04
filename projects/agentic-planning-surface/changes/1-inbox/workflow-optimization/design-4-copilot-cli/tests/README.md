# Feasibility test series: comparison

Each series has its own folder with goal, kit, exact prompts, results and costs.
Labs live in `/tmp/crf-labs/<series>` (throwaway). All runs on 2026-10-29, VS Code Agents host,
Copilot CLI 1.0.105.

| Series | Question | Outcome | Cost (USD) | Key finding |
|--------|----------|---------|-----------:|-------------|
| [01 host primitives](./01-host-primitives/README.md) | Do nested sessions, custom agents, `/every`, background wake-up work? | 4/5 pass | about 0.3 | Nested chats can create sessions; custom agents only as subagents (prefix 2.7k vs 29-49k); Driver wakes 5 s after its Coder ends |
| [02 Foreman-driven](./02-foreman-driven/README.md) | Can the Foreman hire Drivers and relay orders? | 7/7 pass | 1.11 (4 CRs + 1 reopen) | Works end to end in 5 min; Opus Foreman = 53 % of cost; dependent CR branched from `main`; fixed `/every` cannot be stopped |
| [03 Foreman A/B + self-paced](./03-foreman-ab/README.md) | Self-paced watchdog, stacked bases, Opus vs Sol | **Abandoned** | about 0.3 | **A scheduled turn that calls a host tool hangs forever** (3/3); Stop re-arms a self-paced schedule for 30 min |
| [04 Foreman A/B event-driven](./04-foreman-ab-event-driven/README.md) | Same, without watchdog | 04a 5/5, 04b 4/5 | 04a 1.06, 04b **0.68** | Sol Foreman -69 %; stacked bases work; `delete_session` works on independent Drivers but erases telemetry; Sol drops `relationship: independent` |
| [05 nested hierarchy](./05-nested-hierarchy/README.md) | Drivers nested in an independent Foreman session | **Aborted** | n/a | Hierarchy visible in the UI |
| [06 nested + steering](./06-nested-steered/README.md) | Nested Drivers, no state script, mid-run add + change, self-stopping heartbeat | 06: wedge; 06b: 7/7 | 06: 0.55; 06b: **0.62** | **An active `/every` makes host tools hang even in normal turns**; without it, steering works; deleting the Foreman session removes all nested Drivers |
| [07 dynamic workflow](./07-dynamic-workflow/README.md) | Workflow code replaces Foreman and Driver judgement | 7/7 | **0.028** | No main-agent tokens at all; steering through an inbox file; 22× cheaper than 06b |

## Cost per CR across series

| Series | Foreman model | CRs | Total | Per CR | Foreman share |
|--------|---------------|----:|------:|-------:|--------------:|
| Simulation (design 3, before this folder) | Opus 4.8 | 5 | 2.28 | 0.46 | n/a (Drivers on Opus) |
| 02 | Opus 5.5 | 4 (+1 reopen) | 1.11 | 0.28 | 53 % |
| 04a | Opus 5.5 | 5 (+1 order) | 1.06 | 0.21 | 55 % |
| 04b | **gpt-6.1-sol** | 5 (+1 order) | **0.68** | **0.14** | 27 % |
| 06b | gpt-6.1-sol, no state script | 5 (+1 change) | 0.62 | 0.12 | 32 % |
| 07 | **workflow code** | 5 (+1 change, +1 defect fix) | **0.028** | **0.006** | 0 % |

The full comparison and recommendations are in [03-comparison-report.md](../03-comparison-report.md).

## Design decisions supported so far

1. Foreman on `gpt-6.1-sol` (not Opus): same outcome, -69 % Foreman cost, 30-min cache TTL.
2. No `/every` watchdog in the VS Code host: Foreman is event-driven only.
3. Drivers are `independent` sessions (kill switch), hired with an explicit base branch for
   dependencies (stack), and their cost is read before `delete_session`.
4. Coder and Inspector on `gpt-5.6-luna` custom agents: 3-4 % of the bill; not worth optimising.
5. Next lever: the Driver main-session prefix (about 33k tokens × 9 calls ≈ $0.075 per CR).
