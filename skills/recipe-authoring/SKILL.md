# Recipe Authoring Skill

Use when drafting, explaining, validating, or revising quantization recipes.

## Workflow

1. Call `synthesize_quantization_recipe`.
2. Explain recipe tradeoffs to the engineer.
3. Call `validate_quantization_recipe`.
4. If valid, request approval or call `approve_quantization_recipe`.
5. If blocked, ask for the missing fields returned by validation.

## Recipe Must Include

- model source,
- quantization candidates,
- calibration strategy,
- evaluation dataset and metrics,
- compute-pool selector,
- acceptance gates,
- device-farm matrix if mobile/edge,
- fallback and rollback plan.

