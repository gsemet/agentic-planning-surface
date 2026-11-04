# Design 4: Copilot CLI change-request factory

Knowledge base and design for a token-cost-controlled multi-agent workflow on GitHub Copilot CLI.

| File | Content |
|------|---------|
| [00-requirements.md](./00-requirements.md) | Roles, live-intervention requirement, user decisions |
| [01-design.md](./01-design.md) | Topology, roles, cost levers, intervention flows, risks |
| [02-test-protocol.md](./02-test-protocol.md) | Feasibility tests with credit caps and pass criteria |
| [03-comparison-report.md](./03-comparison-report.md) | Session factory vs dynamic workflow: costs, capabilities, recommendations |
| [04-handoff.md](./04-handoff.md) | **Start here in a new session**: state, constraints, series 08 protocol, reports to update |
| [tests/](./tests/README.md) | Feasibility series 01–07 with kits, results and costs |
| [evidence/local-telemetry-findings.md](./evidence/local-telemetry-findings.md) | Measured prices, cache TTLs, simulation costs, SDK surface |
| [evidence/research-billing.md](./evidence/research-billing.md) | Web research: token billing since June 2026 |
| [evidence/research-copilot-cli.md](./evidence/research-copilot-cli.md) | Web research: CLI subagents, sessions, scheduling, SDK |
| [evidence/cli-help-1.0.105/](./evidence/cli-help-1.0.105/) | Raw `copilot help` captures |
| [evidence/scripts/session_cost.py](./evidence/scripts/session_cost.py) | Per-agent cost from `events.jsonl` |
