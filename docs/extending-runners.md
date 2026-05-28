# Extending Runners

The default job runner is a simulation runner. Replace it with production adapters by keeping the same job lifecycle and result contracts. In the enterprise architecture, this runner sits behind the control plane and executes work on registered `compute_nodes`.

## Task Template Shape

A production task template should define:

```json
{
  "template_id": "awq_quantize_llm_v1",
  "description": "AWQ INT4 quantization for decoder-only LLMs.",
  "requires_gpu": true,
  "image": "registry.example.com/ai/llm-opt:cu124-v3",
  "entrypoint": "python /opt/tools/quantize_awq.py",
  "allowed_args_schema": {
    "model_path": "string",
    "calib_path": "string",
    "w_bit": "integer",
    "q_group_size": "integer"
  },
  "required_resources": {
    "gpu_count": 1,
    "min_gpu_memory_gb": 40
  }
}
```

## Adapter Contract

A runner adapter should:

- receive a job record,
- validate lease and workspace,
- materialize command arguments from approved template only,
- stream logs back to job metadata,
- emit metrics samples,
- register artifacts through `ArtifactManager`,
- mark terminal status.

## Suggested Production Backends

- Single server: Docker + NVIDIA Container Toolkit.
- HPC: Slurm with per-job cgroup accounting.
- Kubernetes: Jobs with GPU resource requests and node selectors.
- Ray: distributed model evaluation and benchmark.
- Internal platform: wrap existing training/inference job APIs.
- Device farm: wrap Android/iOS phone-lab APIs and report KPI matrices back through `DeviceFarm`.

## Migration Path

1. Keep the simulation runner for local tests.
2. Add a new adapter module under `src/model_optimization_mcp/adapters/`.
3. Add an environment variable such as `MOMCP_RUNNER_BACKEND=docker`.
4. Move template execution from `JobManager._complete_result` to adapter-specific handlers.
5. Keep artifact and status schemas stable so agents do not need to change.
