# PTQ Execution Skill

Use after a recipe has been validated and approved.

## Workflow

1. Ensure a valid `lease_id` exists.
2. Run `run_quantization`.
3. Poll `get_job_status`.
4. Run `run_quantized_eval`.
5. Run `run_benchmark`.
6. Release the lease when no further GPU work is needed.

## Failure Handling

- Call `analyze_job_failure` before retrying.
- If accuracy fails, prefer recipe revision over ad hoc parameter changes.
- If resource is insufficient, request a different lease or pool.

