# GPU Capacity Planning Skill

Use when a recipe is ready to execute on shared GPU infrastructure.

## Workflow

1. Call `list_compute_pools`.
2. Call `select_compute_pool` with `recipe_id`.
3. Call `create_execution_plan_from_recipe`.
4. Call `estimate_resource_need`.
5. Call `request_resource_lease`.

## Rules

- Do not choose GPU IDs manually.
- Respect queued leases.
- Prefer compute-pool selection from MCP over local assumptions.

