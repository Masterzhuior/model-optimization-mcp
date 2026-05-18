# Agent Skill Pack

This repository includes a portable skill prompt in `skills/model-onboarding/SKILL.md`. The goal is to teach generic local agents how to operate the MCP server safely.

## Principle

The skill is guidance, not security. The MCP server must enforce safety even if an agent ignores the skill.

## Recommended Skill Behavior

Agents should:

- Prefer guided tools such as `start_model_onboarding`, `run_onboarding_stage`, and `get_next_recommended_action`.
- Never run arbitrary SSH or shell commands on the GPU server.
- Always request a GPU lease before GPU work.
- Poll job status instead of blocking indefinitely.
- Read job logs only when a job is running long or failed.
- Stop when the server returns `waiting_for_approval`.
- Summarize artifact IDs, metrics, and risks at the end.

## Human Intervention Points

Agents should stop and ask the engineer when:

- data permission is missing,
- production promotion requires approval,
- accuracy drop exceeds target,
- benchmark result misses the SLO,
- quota is exhausted,
- the server reports ambiguous failure diagnosis,
- a destructive cleanup is requested with `dry_run=false`.

## Example Engineer Prompt

```text
Use the Model Optimization MCP server to onboard s3://models/qwen2.5-7b-instruct
for H100 serving. Try INT4 first, accept at most 1% accuracy drop, and generate
a final report with artifact lineage.
```

## Example Agent Plan

```text
1. health_check
2. start_model_onboarding
3. run_onboarding_stage inspect_model
4. request_resource_lease for baseline
5. run_onboarding_stage baseline_eval
6. run_onboarding_stage baseline_benchmark
7. run_onboarding_stage recommend_recipes
8. request_resource_lease for quantization
9. run_onboarding_stage quantize_candidates
10. run_onboarding_stage quantized_eval
11. run_onboarding_stage benchmark_candidates
12. run_onboarding_stage compare
13. generate_onboarding_report
```

