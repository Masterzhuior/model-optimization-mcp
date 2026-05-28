# Agent Skill Pack

This repository treats skills as first-class workflow executors. MCP is not expected to do every step.

## Execution Types

| Executor | Use it for |
| --- | --- |
| `local_skill` | Reasoning, clarification, explanation, local config/package generation. |
| `mcp_tool` | Shared state, policy, remote execution, artifact lineage, KPI reports. |
| `human_approval` | GPU budget, data access, production promotion, risky tradeoffs. |
| `hybrid` | Skill reasons while MCP records state or executes a controlled action. |
| `external_system` | Ticketing, model registry, approval, or device farm outside MCP. |

## Skill Set

| Skill | Role |
| --- | --- |
| `intent-intake` | Convert vague requests into structured requirements and questions. |
| `recipe-authoring` | Draft, validate, explain, and revise recipes. |
| `gpu-capacity-planning` | Use MCP capacity and pool-selection tools. |
| `ptq-execution` | Run approved PTQ candidates through MCP. |
| `device-farm-evaluation` | Package and submit artifacts to device-farm testing. |
| `kpi-regression-analysis` | Analyze KPI failures and create recipe feedback. |
| `release-reporting` | Generate final report and promotion recommendation. |

## Recommended Agent Behavior

When the engineer says something like:

```text
用 PTQ 量化 Qwen3.6 模型
```

The agent should not immediately run quantization. It should:

1. Use the intake skill to identify missing information.
2. Call `start_quantization_intake`.
3. Ask only the necessary questions returned by MCP.
4. Call `answer_intake_questions`.
5. Use the recipe-authoring skill to explain tradeoffs.
6. Call `synthesize_quantization_recipe`.
7. Call `validate_quantization_recipe`.
8. Generate a hybrid plan with `generate_hybrid_workflow_plan`.
9. Ask for approval if required.
10. Use MCP to select compute pool and run remote jobs.
11. Use device-farm tools when the target is mobile or edge.
12. Use KPI regression skill if results fail.
13. Create recipe feedback and a revised recipe when needed.

## What Skills Should Not Do

Skills should not:

- SSH into GPU servers,
- pick GPU IDs manually,
- bypass leases,
- mutate artifacts outside MCP,
- promote production artifacts without approval,
- delete shared workspaces or caches directly.

## Final Response Contract

At the end, the agent should report:

- recipe ID and version,
- artifact ID and stage,
- compute pool used,
- quantization method and fallback candidates,
- server eval and benchmark result,
- device-farm KPI report,
- failures and root-cause hypotheses,
- recipe feedback or revision ID,
- approval or promotion status.

