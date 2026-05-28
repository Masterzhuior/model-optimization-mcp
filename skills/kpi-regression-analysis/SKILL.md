# KPI Regression Analysis Skill

Use when server eval or device-farm KPI reports fail.

## Workflow

1. Call `analyze_kpi_regression`.
2. Explain likely root causes.
3. Call `create_recipe_feedback`.
4. Call `create_recipe_revision_from_feedback`.
5. Ask the engineer before approving the revised recipe.

## Common Strategies

- accuracy regression: increase calibration samples, run sensitivity analysis, use mixed precision.
- latency regression: change backend/delegate, inspect kernels, adjust packaging.
- memory regression: change cache strategy, reduce max sequence length, use mixed precision.

