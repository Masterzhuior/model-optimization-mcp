# Model Onboarding Operator Skill

Use this skill when the user asks to onboard a model, run inference optimization, quantize a model, evaluate a quantized model, benchmark serving performance, inspect GPU resources, or generate a model optimization report.

## Operating Rules

- Prefer the `model-optimization-mcp` server tools.
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
2. Call `start_model_onboarding`.
3. Call `run_onboarding_stage` for `inspect_model`.
4. Call `get_next_recommended_action`.
5. Before GPU stages, call `estimate_resource_need`.
6. Call `request_resource_lease`.
7. Call `run_onboarding_stage` with `lease_id`.
8. Poll `get_job_status` until terminal.
9. Continue with `get_next_recommended_action`.
10. Generate a final report with `generate_onboarding_report`.
11. Release the lease with `release_resource_lease` when no longer needed.

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

