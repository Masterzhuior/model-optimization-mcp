# Model Onboarding Operator Skill

Use this skill when the user asks to onboard a model, run inference optimization, quantize a model, evaluate a quantized model, benchmark serving performance, inspect GPU resources, run device-farm validation, or generate a model optimization report.

## Operating Rules

- Prefer the `model-optimization-mcp` server tools for shared state and remote execution.
- Use local skills for intent intake, recipe explanation, KPI regression analysis, and report writing.
- Do not SSH into GPU servers for model optimization work.
- Do not run arbitrary shell commands for quantization, evaluation, benchmark, profiling, or artifact export.
- Do not choose GPU IDs manually from `nvidia-smi`.
- Every GPU stage must use a server-issued `lease_id`.
- Long-running operations are asynchronous; submit the job, then poll `get_job_status`.
- If a job fails, call `analyze_job_failure` before retrying.
- If a tool returns `waiting_for_approval`, stop and ask the engineer to approve.
- If a tool returns `waiting_for_resource`, summarize queue/resource status and ask whether to wait, reduce scope, or schedule later.
- Preserve artifact IDs, report URI, accuracy delta, benchmark speedup, and risk notes in the final response.

## Preferred Guided Workflow

1. Call `health_check`.
2. Call `start_quantization_intake`.
3. Ask required questions returned by MCP.
4. Call `answer_intake_questions`.
5. Call `synthesize_quantization_recipe`.
6. Call `validate_quantization_recipe`.
7. Call `generate_hybrid_workflow_plan`.
8. Ask for approval when required, then call `approve_quantization_recipe`.
9. Call `select_compute_pool` and `create_execution_plan_from_recipe`.
10. Before GPU stages, call `estimate_resource_need` and `request_resource_lease`.
11. Run PTQ/eval/benchmark tools.
12. If target is mobile/edge, run device-farm tools and KPI analysis.
13. Generate a final report with `generate_onboarding_report`.
14. Release the lease with `release_resource_lease` when no longer needed.

## Retry Strategy

If accuracy drops too much:

- try a safer recipe such as INT8 weight-only,
- increase calibration samples,
- exclude sensitive layers if supported by the registered recipe,
- ask the engineer before accepting a larger degradation.

If GPU memory is insufficient:

- request a larger lease,
- reduce max sequence length,
- use a smaller batch size,
- try a more conservative backend.

If performance misses target:

- run `run_profiler`,
- compare benchmark results,
- try compile/export path,
- check backend compatibility.

## Final Response Shape

Summarize:

- chosen artifact ID and URI,
- quantization method and recipe,
- accuracy delta,
- throughput/latency/memory changes,
- report URI,
- remaining risks or required approvals.
