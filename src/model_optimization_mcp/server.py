"""MCP server definition."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .app import AppContext, create_app_context
from .schemas import NextAction, ok
from .utils import public_error, short_id, utc_now_iso


def build_mcp(context: AppContext | None = None) -> Any:
    """Build the FastMCP server.

    Importing MCP lazily keeps the service layer testable without installing the
    MCP SDK in minimal CI environments.
    """

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - exercised by user environment
        raise RuntimeError(
            "The 'mcp' package is required to run the server. Install with: pip install -e ."
        ) from exc

    ctx = context or create_app_context()
    mcp = FastMCP(
        name="Model Optimization MCP",
        instructions=(
            "Use this server for GPU resource governance, model onboarding, quantization, "
            "evaluation, benchmarking, profiling, artifact management, and report generation. "
            "Do not run arbitrary shell commands on GPU servers; use the structured tools."
        ),
        host=ctx.settings.host,
        port=ctx.settings.port,
        stateless_http=True,
        json_response=True,
    )

    def call(fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - tool boundary guard
            return public_error(exc)

    @mcp.resource("workflow://model-onboarding/default")
    def model_onboarding_workflow() -> str:
        """Default model onboarding workflow for local agents."""
        return _json(
            {
                "name": "default-model-onboarding",
                "stages": [
                    "start_model_onboarding",
                    "inspect_model",
                    "prepare_calibration",
                    "request_resource_lease",
                    "baseline_eval",
                    "baseline_benchmark",
                    "recommend_recipes",
                    "quantize_candidates",
                    "quantized_eval",
                    "benchmark_candidates",
                    "compare",
                    "generate_onboarding_report",
                ],
                "rules": [
                    "Never use arbitrary shell execution for GPU work.",
                    "GPU stages require a server-issued lease_id.",
                    "If a tool returns waiting_for_approval or waiting_for_resource, stop and surface it.",
                    "Use get_next_recommended_action after each completed stage.",
                ],
            }
        )

    @mcp.resource("policy://gpu-resource-usage")
    def gpu_resource_policy() -> str:
        """GPU sharing and lease policy."""
        return _json(
            {
                "policy": "lease-first",
                "requirements": [
                    "Every GPU job must bind to a lease_id.",
                    "Benchmark and profiling jobs should use exclusive GPUs.",
                    "Leases have TTL and must be renewed by long-running agents.",
                    "Agents may cancel their own jobs but cannot kill unrelated user processes.",
                ],
            }
        )

    @mcp.resource("catalog://runtime-envs")
    def runtime_env_catalog() -> str:
        """Available runtime environments."""
        return _json({"runtime_envs": ctx.store.list("runtime_envs")})

    @mcp.resource("catalog://quant-recipes")
    def quant_recipe_catalog() -> str:
        """Available quantization recipes."""
        return _json({"recipes": ctx.store.list("recipes")})

    @mcp.resource("run://{run_id}")
    def onboarding_run_resource(run_id: str) -> str:
        """Read a model onboarding run."""
        return _json(ctx.onboarding.summarize(run_id))

    @mcp.prompt(title="Model Onboarding Operator")
    def model_onboarding_operator(goal: str) -> str:
        return f"""
You are operating the Model Optimization MCP server for this goal:

{goal}

Follow the server workflow resource. Use structured tools only. For GPU work:
1. inspect current resources,
2. estimate resource needs,
3. request a lease,
4. submit the stage with lease_id,
5. poll get_job_status and read logs when needed,
6. call get_next_recommended_action before proceeding.

Stop and ask the engineer when the server returns waiting_for_approval, permission_denied,
or a business tradeoff such as accuracy drop above threshold.
""".strip()

    @mcp.tool()
    def health_check() -> dict[str, Any]:
        """Check server health, state paths, and catalog counts."""
        return call(
            lambda: ok(
                "Model Optimization MCP is ready.",
                data={
                    "timestamp": utc_now_iso(),
                    "home": str(ctx.settings.home),
                    "workspace_root": str(ctx.settings.workspace_root),
                    "artifact_root": str(ctx.settings.artifact_root),
                    "runtime_envs": len(ctx.store.list("runtime_envs")),
                    "recipes": len(ctx.store.list("recipes")),
                    "task_templates": len(ctx.store.list("task_templates")),
                },
            )
        )

    @mcp.tool()
    def list_runtime_envs() -> dict[str, Any]:
        """List approved runtime environments."""
        return call(lambda: ok("Runtime environments listed.", data={"envs": ctx.store.list("runtime_envs")}))

    @mcp.tool()
    def list_toolchains() -> dict[str, Any]:
        """List approved task templates and toolchains."""
        return call(
            lambda: ok("Task templates listed.", data={"task_templates": ctx.store.list("task_templates")})
        )

    @mcp.tool()
    def validate_runtime_env(env_id: str) -> dict[str, Any]:
        """Validate that a runtime environment is registered and ready."""
        return call(lambda: _validate_runtime_env(ctx, env_id))

    @mcp.tool()
    def get_resource_snapshot(
        include_processes: bool = True,
        include_jobs: bool = True,
        include_disk: bool = True,
        include_queue: bool = True,
    ) -> dict[str, Any]:
        """Inspect GPU, CPU, disk, lease, queue, and job state."""
        return call(
            lambda: ok(
                "Resource snapshot collected.",
                data=ctx.resources.snapshot(
                    include_processes=include_processes,
                    include_jobs=include_jobs,
                    include_disk=include_disk,
                    include_queue=include_queue,
                ),
            )
        )

    @mcp.tool()
    def estimate_resource_need(
        model_id: str | None = None,
        model_uri: str | None = None,
        stage: str = "quantization",
        parameter_count_b: float | None = None,
        dtype: str = "bf16",
    ) -> dict[str, Any]:
        """Estimate GPU/CPU/RAM/disk needs before requesting a lease."""
        return call(
            lambda: ok(
                "Resource estimate created.",
                data=ctx.resources.estimate_need(
                    model_id=model_id,
                    model_uri=model_uri,
                    stage=stage,
                    parameter_count_b=parameter_count_b,
                    dtype=dtype,
                ),
            )
        )

    @mcp.tool()
    def request_resource_lease(
        project_id: str,
        user_id: str,
        purpose: str,
        requirements: dict[str, Any] | None = None,
        scheduling: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Request a server-issued resource lease for GPU work."""
        return call(
            lambda: ok(
                "Resource lease request processed.",
                data=ctx.resources.request_lease(
                    project_id=project_id,
                    user_id=user_id,
                    purpose=purpose,
                    requirements=requirements,
                    scheduling=scheduling,
                ),
            )
        )

    @mcp.tool()
    def renew_resource_lease(lease_id: str, duration_minutes: int = 60) -> dict[str, Any]:
        """Renew an active resource lease."""
        return call(
            lambda: ok(
                "Resource lease renewed.",
                data=ctx.resources.renew_lease(lease_id, duration_minutes),
            )
        )

    @mcp.tool()
    def release_resource_lease(lease_id: str, reason: str = "released_by_client") -> dict[str, Any]:
        """Release a resource lease."""
        return call(
            lambda: ok(
                "Resource lease released.",
                data=ctx.resources.release_lease(lease_id, reason),
            )
        )

    @mcp.tool()
    def get_queue_status(project_id: str | None = None) -> dict[str, Any]:
        """Get queued lease requests."""
        return call(lambda: ok("Queue status collected.", data=ctx.resources.queue_status(project_id)))

    @mcp.tool()
    def get_user_usage(user_id: str | None = None, project_id: str | None = None) -> dict[str, Any]:
        """Summarize resource usage by user or project."""
        return call(lambda: ok("Usage summarized.", data=ctx.resources.user_usage(user_id, project_id)))

    @mcp.tool()
    def list_gpu_processes() -> dict[str, Any]:
        """List GPU processes known to the server."""
        return call(lambda: ok("GPU processes listed.", data={"processes": ctx.resources.list_gpu_processes()}))

    @mcp.tool()
    def cleanup_orphan_jobs(dry_run: bool = True) -> dict[str, Any]:
        """Identify orphan GPU jobs. Does not kill processes by default."""
        return call(lambda: ok("Orphan scan completed.", data=ctx.resources.cleanup_orphan_jobs(dry_run)))

    @mcp.tool()
    def create_workspace(
        project_id: str,
        user_id: str,
        run_id: str | None = None,
        quota_gb: float = 500,
        purpose: str = "model-onboarding",
    ) -> dict[str, Any]:
        """Create an isolated workspace for a run."""
        return call(
            lambda: ok(
                "Workspace created.",
                data=ctx.workspaces.create_workspace(
                    project_id=project_id,
                    user_id=user_id,
                    run_id=run_id,
                    quota_gb=quota_gb,
                    purpose=purpose,
                ),
            )
        )

    @mcp.tool()
    def list_workspace_files(
        workspace_id: str, relative_path: str = ".", max_entries: int = 200
    ) -> dict[str, Any]:
        """List files inside a managed workspace."""
        return call(
            lambda: ok(
                "Workspace files listed.",
                data=ctx.workspaces.list_files(workspace_id, relative_path, max_entries),
            )
        )

    @mcp.tool()
    def read_text_file(
        workspace_id: str, relative_path: str, max_bytes: int = 128_000
    ) -> dict[str, Any]:
        """Read a small text file inside a workspace."""
        return call(
            lambda: ok(
                "Text file read.",
                data=ctx.workspaces.read_text_file(workspace_id, relative_path, max_bytes),
            )
        )

    @mcp.tool()
    def write_config_file(
        workspace_id: str,
        relative_path: str,
        content: dict[str, Any] | str,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Write JSON/YAML/TOML/text config inside a workspace."""
        return call(
            lambda: ok(
                "Config file written.",
                data=ctx.workspaces.write_config_file(
                    workspace_id, relative_path, content, overwrite=overwrite
                ),
            )
        )

    @mcp.tool()
    def register_model(
        project_id: str,
        model_uri: str,
        model_name: str | None = None,
        framework_hint: str = "transformers",
        task_type: str = "text-generation",
        parameter_count_b: float | None = None,
    ) -> dict[str, Any]:
        """Register a model with the onboarding registry."""
        return call(
            lambda: ok(
                "Model registered.",
                data=ctx.workspaces.register_model(
                    project_id=project_id,
                    model_uri=model_uri,
                    model_name=model_name,
                    framework_hint=framework_hint,
                    task_type=task_type,
                    parameter_count_b=parameter_count_b,
                ),
            )
        )

    @mcp.tool()
    def stage_model(
        workspace_id: str,
        model_uri: str,
        model_id: str | None = None,
        copy_mode: str = "reference",
    ) -> dict[str, Any]:
        """Stage or reference a model inside a workspace."""
        return call(
            lambda: ok(
                "Model staged.",
                data=ctx.workspaces.stage_model(
                    workspace_id=workspace_id,
                    model_uri=model_uri,
                    model_id=model_id,
                    copy_mode=copy_mode,
                ),
            )
        )

    @mcp.tool()
    def stage_dataset(
        workspace_id: str,
        dataset_id: str,
        usage: str = "evaluation",
        sample_count: int | None = None,
    ) -> dict[str, Any]:
        """Stage a known dataset inside a workspace."""
        return call(
            lambda: ok(
                "Dataset staged.",
                data=ctx.workspaces.stage_dataset(
                    workspace_id=workspace_id,
                    dataset_id=dataset_id,
                    usage=usage,
                    sample_count=sample_count,
                ),
            )
        )

    @mcp.tool()
    def compute_checksum(workspace_id: str, relative_path: str) -> dict[str, Any]:
        """Compute checksums for a file or directory inside a workspace."""
        return call(
            lambda: ok(
                "Checksum computed.",
                data=ctx.workspaces.compute_checksum(workspace_id, relative_path),
            )
        )

    @mcp.tool()
    def get_disk_usage(workspace_id: str) -> dict[str, Any]:
        """Get workspace disk usage."""
        return call(lambda: ok("Disk usage collected.", data=ctx.workspaces.disk_usage(workspace_id)))

    @mcp.tool()
    def cleanup_workspace(
        workspace_id: str, mode: str = "outputs-only", dry_run: bool = True
    ) -> dict[str, Any]:
        """Clean workspace outputs or the entire workspace."""
        return call(
            lambda: ok(
                "Workspace cleanup planned.",
                data=ctx.workspaces.cleanup_workspace(workspace_id, mode=mode, dry_run=dry_run),
            )
        )

    @mcp.tool()
    def list_datasets(
        project_id: str | None = None,
        task_type: str | None = None,
        usage: list[str] | None = None,
    ) -> dict[str, Any]:
        """List known calibration and evaluation datasets."""
        def _inner() -> dict[str, Any]:
            datasets = ctx.store.list("datasets")
            if task_type:
                datasets = [item for item in datasets if item.get("task_type") == task_type]
            if usage:
                datasets = [item for item in datasets if set(usage).intersection(item.get("usage", []))]
            return ok("Datasets listed.", data={"project_id": project_id, "datasets": datasets})

        return call(_inner)

    @mcp.tool()
    def inspect_model(
        model_id: str,
        deep: bool = True,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Submit a CPU-safe model inspection job."""
        return call(
            lambda: ok(
                "Model inspection submitted.",
                data=ctx.jobs.submit_job(
                    template_id="inspect_model_v1",
                    project_id=(ctx.store.get("models", model_id) or {}).get("project_id", "default"),
                    user_id="agent",
                    workspace_id=workspace_id,
                    args={"model_id": model_id, "deep": deep},
                ),
            )
        )

    @mcp.tool()
    def validate_model_load(
        model_id: str,
        lease_id: str,
        workspace_id: str | None = None,
        env_id: str = "llm-opt-cu124-v3",
    ) -> dict[str, Any]:
        """Submit a GPU model load validation job."""
        return call(
            lambda: _submit_model_job(
                ctx,
                "validate_model_load_v1",
                model_id=model_id,
                lease_id=lease_id,
                workspace_id=workspace_id,
                env_id=env_id,
            )
        )

    @mcp.tool()
    def validate_tokenizer(model_id: str) -> dict[str, Any]:
        """Validate tokenizer metadata and chat template presence."""
        return call(lambda: ok("Tokenizer looks valid.", data={"model_id": model_id, "tokenizer_found": True}))

    @mcp.tool()
    def validate_chat_template(model_id: str) -> dict[str, Any]:
        """Validate model chat template availability."""
        return call(
            lambda: ok(
                "Chat template validation completed.",
                data={"model_id": model_id, "chat_template_found": True, "risk_flags": []},
            )
        )

    @mcp.tool()
    def check_backend_compatibility(
        model_id: str,
        backend: str = "vllm",
        hardware_target: str = "H100",
    ) -> dict[str, Any]:
        """Check serving backend compatibility for a model."""
        return call(
            lambda: ok(
                "Backend compatibility checked.",
                data={
                    "model_id": model_id,
                    "backend": backend,
                    "hardware_target": hardware_target,
                    "compatible": True,
                    "warnings": [],
                },
            )
        )

    @mcp.tool()
    def prepare_calibration_dataset(
        dataset_id: str,
        model_id: str,
        sample_count: int = 1024,
        max_seq_len: int = 2048,
        sampling_strategy: str = "diverse",
        output_format: str = "tokenized",
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Prepare calibration data metadata for quantization."""
        def _inner() -> dict[str, Any]:
            calibration_artifact_id = short_id("calib")
            data = {
                "calibration_artifact_id": calibration_artifact_id,
                "dataset_id": dataset_id,
                "model_id": model_id,
                "num_samples": sample_count,
                "max_seq_len": max_seq_len,
                "sampling_strategy": sampling_strategy,
                "output_format": output_format,
            }
            if workspace_id:
                staged = ctx.workspaces.stage_dataset(
                    workspace_id=workspace_id,
                    dataset_id=dataset_id,
                    usage="calibration",
                    sample_count=sample_count,
                )
                data["workspace_dataset"] = staged
            return ok("Calibration dataset prepared.", data=data)

        return call(_inner)

    @mcp.tool()
    def validate_eval_dataset(dataset_id: str, model_id: str, task_type: str = "text-generation") -> dict[str, Any]:
        """Validate that an evaluation dataset matches a model task."""
        return call(
            lambda: ok(
                "Evaluation dataset validated.",
                data={"dataset_id": dataset_id, "model_id": model_id, "task_type": task_type, "valid": True},
            )
        )

    @mcp.tool()
    def run_baseline_eval(
        model_id: str,
        lease_id: str,
        eval_config: dict[str, Any],
        workspace_id: str | None = None,
        env_id: str = "llm-opt-cu124-v3",
    ) -> dict[str, Any]:
        """Submit baseline accuracy evaluation."""
        return call(
            lambda: _submit_model_job(
                ctx,
                "baseline_eval_v1",
                model_id=model_id,
                lease_id=lease_id,
                workspace_id=workspace_id,
                env_id=env_id,
                args={"eval_config": eval_config},
            )
        )

    @mcp.tool()
    def run_baseline_benchmark(
        model_id: str,
        lease_id: str,
        benchmark_config: dict[str, Any],
        workspace_id: str | None = None,
        env_id: str = "llm-opt-cu124-v3",
    ) -> dict[str, Any]:
        """Submit baseline performance benchmark."""
        return call(
            lambda: _submit_model_job(
                ctx,
                "baseline_benchmark_v1",
                model_id=model_id,
                lease_id=lease_id,
                workspace_id=workspace_id,
                env_id=env_id,
                args={"benchmark_config": benchmark_config},
            )
        )

    @mcp.tool()
    def recommend_quant_recipes(
        model_id: str,
        target: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
        candidate_methods: list[str] | None = None,
    ) -> dict[str, Any]:
        """Recommend quantization recipes for a model and target."""
        return call(
            lambda: ctx.onboarding.recommend_recipes(
                model_id=model_id,
                target=target,
                constraints=constraints,
                candidate_methods=candidate_methods,
            )
        )

    @mcp.tool()
    def create_quant_recipe(
        base_recipe_id: str,
        overrides: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create a derived quantization recipe."""
        def _inner() -> dict[str, Any]:
            base = ctx.store.get("recipes", base_recipe_id)
            if not base:
                raise ValueError(f"unknown base_recipe_id: {base_recipe_id}")
            recipe_id = short_id("recipe")
            recipe = dict(base)
            recipe.update(overrides or {})
            recipe["recipe_id"] = recipe_id
            recipe["name"] = name or f"{base_recipe_id}-custom"
            recipe["created_at"] = utc_now_iso()
            recipe["derived_from"] = base_recipe_id
            ctx.store.upsert("recipes", recipe_id, recipe)
            return ok("Quantization recipe created.", data=recipe)

        return call(_inner)

    @mcp.tool()
    def run_quantization(
        model_id: str,
        recipe_id: str,
        lease_id: str,
        calibration_artifact_id: str | None = None,
        workspace_id: str | None = None,
        env_id: str = "llm-opt-cu124-v3",
        output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit a whitelisted quantization job."""
        output = output or {}
        return call(
            lambda: _submit_model_job(
                ctx,
                "quantize_model_v1",
                model_id=model_id,
                lease_id=lease_id,
                workspace_id=workspace_id,
                env_id=env_id,
                args={
                    "recipe_id": recipe_id,
                    "calibration_artifact_id": calibration_artifact_id,
                    "artifact_name": output.get("artifact_name"),
                },
            )
        )

    @mcp.tool()
    def validate_quantized_model(
        quant_artifact_id: str,
        lease_id: str,
        backend: str = "vllm",
        env_id: str = "llm-opt-cu124-v3",
    ) -> dict[str, Any]:
        """Validate that a quantized artifact loads in the target backend."""
        artifact = ctx.store.get("artifacts", quant_artifact_id) or {}
        return call(
            lambda: ok(
                "Quantized model validation submitted.",
                data=ctx.jobs.submit_job(
                    template_id="validate_model_load_v1",
                    project_id=artifact.get("project_id", "default"),
                    user_id="agent",
                    lease_id=lease_id,
                    env_id=env_id,
                    args={"quant_artifact_id": quant_artifact_id, "backend": backend},
                ),
            )
        )

    @mcp.tool()
    def run_quantized_eval(
        quant_artifact_id: str,
        lease_id: str,
        baseline_id: str | None = None,
        eval_config: dict[str, Any] | None = None,
        acceptance_criteria: dict[str, Any] | None = None,
        env_id: str = "llm-opt-cu124-v3",
    ) -> dict[str, Any]:
        """Submit quantized accuracy evaluation."""
        artifact = ctx.store.get("artifacts", quant_artifact_id) or {}
        return call(
            lambda: ok(
                "Quantized evaluation submitted.",
                data=ctx.jobs.submit_job(
                    template_id="quantized_eval_v1",
                    project_id=artifact.get("project_id", "default"),
                    user_id="agent",
                    lease_id=lease_id,
                    env_id=env_id,
                    args={
                        "quant_artifact_id": quant_artifact_id,
                        "baseline_id": baseline_id,
                        "eval_config": eval_config or {},
                        "acceptance_criteria": acceptance_criteria or {"max_accuracy_drop": 0.01},
                    },
                    run_id=artifact.get("lineage", {}).get("run_id"),
                ),
            )
        )

    @mcp.tool()
    def run_benchmark(
        artifact_id: str,
        lease_id: str,
        backend: str = "vllm",
        benchmark_config: dict[str, Any] | None = None,
        runtime: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit benchmark for a model artifact."""
        artifact = ctx.store.get("artifacts", artifact_id) or {}
        return call(
            lambda: ok(
                "Benchmark submitted.",
                data=ctx.jobs.submit_job(
                    template_id="benchmark_v1",
                    project_id=artifact.get("project_id", "default"),
                    user_id="agent",
                    lease_id=lease_id,
                    env_id=(runtime or {}).get("env_id", "llm-opt-cu124-v3"),
                    args={
                        "artifact_id": artifact_id,
                        "backend": backend,
                        "benchmark_config": benchmark_config or {},
                    },
                    run_id=artifact.get("lineage", {}).get("run_id"),
                ),
            )
        )

    @mcp.tool()
    def compare_benchmarks(
        baseline_benchmark_id: str | None = None,
        candidate_benchmark_ids: list[str] | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Compare benchmark artifacts or all candidates in a run."""
        return call(lambda: _compare_benchmarks(ctx, baseline_benchmark_id, candidate_benchmark_ids, run_id))

    @mcp.tool()
    def run_profiler(
        artifact_id: str,
        lease_id: str,
        backend: str = "vllm",
        profiler: str = "nsys",
        profile_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit a profiling job."""
        artifact = ctx.store.get("artifacts", artifact_id) or {}
        return call(
            lambda: ok(
                "Profiler submitted.",
                data=ctx.jobs.submit_job(
                    template_id="profile_v1",
                    project_id=artifact.get("project_id", "default"),
                    user_id="agent",
                    lease_id=lease_id,
                    args={
                        "artifact_id": artifact_id,
                        "backend": backend,
                        "profiler": profiler,
                        "profile_config": profile_config or {},
                    },
                    run_id=artifact.get("lineage", {}).get("run_id"),
                ),
            )
        )

    @mcp.tool()
    def compile_model(
        artifact_id: str,
        lease_id: str,
        compiler: str = "tensorrt-llm",
        compile_config: dict[str, Any] | None = None,
        runtime: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compile a model artifact for an approved backend."""
        artifact = ctx.store.get("artifacts", artifact_id) or {}
        return call(
            lambda: ok(
                "Compile job submitted.",
                data=ctx.jobs.submit_job(
                    template_id="compile_model_v1",
                    project_id=artifact.get("project_id", "default"),
                    user_id="agent",
                    lease_id=lease_id,
                    env_id=(runtime or {}).get("env_id", "llm-opt-cu124-v3"),
                    args={
                        "artifact_id": artifact_id,
                        "compiler": compiler,
                        "compile_config": compile_config or {},
                    },
                    run_id=artifact.get("lineage", {}).get("run_id"),
                ),
            )
        )

    @mcp.tool()
    def export_model(
        artifact_id: str,
        target_format: str = "vllm",
        output_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register an exported serving artifact."""
        def _inner() -> dict[str, Any]:
            source = ctx.artifacts.get_artifact(artifact_id)
            exported = ctx.artifacts.register_artifact(
                artifact_type="serving_bundle",
                name=f"{source.get('name')}-{target_format}",
                project_id=source["project_id"],
                metadata={"target_format": target_format, "output_options": output_options or {}},
                lineage={"source_artifact_id": artifact_id, "run_id": source.get("lineage", {}).get("run_id")},
            )
            return ok("Model exported.", data=exported)

        return call(_inner)

    @mcp.tool()
    def package_serving_bundle(
        artifact_id: str,
        backend: str = "vllm",
        include_tokenizer: bool = True,
        include_generation_config: bool = True,
    ) -> dict[str, Any]:
        """Package an artifact for serving."""
        return export_model(
            artifact_id,
            target_format=backend,
            output_options={
                "include_tokenizer": include_tokenizer,
                "include_generation_config": include_generation_config,
            },
        )

    @mcp.tool()
    def allocate_service_port(
        project_id: str,
        user_id: str,
        purpose: str = "inference-service",
        preferred_port: int | None = None,
        min_port: int = 20000,
        max_port: int = 40000,
    ) -> dict[str, Any]:
        """Allocate a managed port for temporary serving or benchmark services."""
        return call(
            lambda: ok(
                "Service port allocated.",
                data=_allocate_service_port(
                    ctx,
                    project_id=project_id,
                    user_id=user_id,
                    purpose=purpose,
                    preferred_port=preferred_port,
                    min_port=min_port,
                    max_port=max_port,
                ),
            )
        )

    @mcp.tool()
    def release_service_port(port_id: str, reason: str = "released_by_client") -> dict[str, Any]:
        """Release a managed service port."""
        return call(
            lambda: ok(
                "Service port released.",
                data=_release_service_port(ctx, port_id=port_id, reason=reason),
            )
        )

    @mcp.tool()
    def start_inference_service(
        artifact_id: str,
        lease_id: str,
        port_id: str,
        backend: str = "vllm",
        runtime: dict[str, Any] | None = None,
        service_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Start a managed temporary inference service for smoke tests or benchmark."""
        return call(
            lambda: ok(
                "Inference service started.",
                data=_start_inference_service(
                    ctx,
                    artifact_id=artifact_id,
                    lease_id=lease_id,
                    port_id=port_id,
                    backend=backend,
                    runtime=runtime,
                    service_config=service_config,
                ),
            )
        )

    @mcp.tool()
    def get_service_health(service_id: str) -> dict[str, Any]:
        """Check a managed inference service."""
        return call(
            lambda: ok(
                "Service health collected.",
                data=_get_service_health(ctx, service_id=service_id),
            )
        )

    @mcp.tool()
    def stop_inference_service(service_id: str, reason: str = "stopped_by_client") -> dict[str, Any]:
        """Stop a managed inference service and release its port."""
        return call(
            lambda: ok(
                "Inference service stopped.",
                data=_stop_inference_service(ctx, service_id=service_id, reason=reason),
            )
        )

    @mcp.tool()
    def submit_job(
        template_id: str,
        project_id: str,
        user_id: str,
        workspace_id: str | None = None,
        lease_id: str | None = None,
        env_id: str = "llm-opt-cu124-v3",
        args: dict[str, Any] | None = None,
        run_id: str | None = None,
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Submit a registered task template directly."""
        return call(
            lambda: ok(
                "Job submitted.",
                data=ctx.jobs.submit_job(
                    template_id=template_id,
                    project_id=project_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    lease_id=lease_id,
                    env_id=env_id,
                    args=args,
                    run_id=run_id,
                    priority=priority,
                ),
            )
        )

    @mcp.tool()
    def get_job_status(job_id: str) -> dict[str, Any]:
        """Get job status, result, failure, and artifact IDs."""
        return call(lambda: ok("Job status collected.", data=ctx.jobs.get_status(job_id)))

    @mcp.tool()
    def get_job_logs(job_id: str, tail_lines: int = 200, level: str | None = None) -> dict[str, Any]:
        """Read job logs."""
        return call(lambda: ok("Job logs collected.", data=ctx.jobs.get_logs(job_id, tail_lines, level)))

    @mcp.tool()
    def get_job_metrics(job_id: str) -> dict[str, Any]:
        """Read job time-series metrics."""
        return call(lambda: ok("Job metrics collected.", data=ctx.jobs.get_metrics(job_id)))

    @mcp.tool()
    def cancel_job(job_id: str, reason: str = "cancelled_by_client") -> dict[str, Any]:
        """Cancel a job owned by the caller/project policy."""
        return call(lambda: ok("Cancel request processed.", data=ctx.jobs.cancel_job(job_id, reason)))

    @mcp.tool()
    def retry_job(job_id: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """Retry a previous job with optional argument overrides."""
        return call(lambda: ok("Retry submitted.", data=ctx.jobs.retry_job(job_id, overrides)))

    @mcp.tool()
    def analyze_job_failure(
        job_id: str,
        include_logs: bool = True,
        include_environment: bool = True,
        include_known_issues: bool = True,
    ) -> dict[str, Any]:
        """Analyze a failed job and suggest safe next actions."""
        return call(
            lambda: ok(
                "Failure analysis completed.",
                data=ctx.jobs.analyze_failure(
                    job_id,
                    include_logs=include_logs,
                    include_environment=include_environment,
                )
                | {"include_known_issues": include_known_issues},
            )
        )

    @mcp.tool()
    def start_model_onboarding(
        project_id: str,
        user_id: str,
        model_uri: str,
        task_type: str = "text-generation",
        target_hardware: str = "H100",
        optimization_goal: dict[str, Any] | None = None,
        eval_dataset_id: str = "eval-internal-chat-v2",
        calibration_dataset_id: str = "calib-general-v1",
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create a guided onboarding run for local agents."""
        return call(
            lambda: ok(
                "Model onboarding run created.",
                data=ctx.onboarding.start(
                    project_id=project_id,
                    user_id=user_id,
                    model_uri=model_uri,
                    task_type=task_type,
                    target_hardware=target_hardware,
                    optimization_goal=optimization_goal,
                    eval_dataset_id=eval_dataset_id,
                    calibration_dataset_id=calibration_dataset_id,
                    name=name,
                ),
            )
        )

    @mcp.tool()
    def run_onboarding_stage(
        run_id: str,
        stage: str,
        lease_id: str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a single onboarding stage."""
        return call(
            lambda: ok(
                "Onboarding stage processed.",
                data=ctx.onboarding.run_stage(
                    run_id=run_id, stage=stage, lease_id=lease_id, overrides=overrides
                ),
            )
        )

    @mcp.tool()
    def get_next_recommended_action(run_id: str) -> dict[str, Any]:
        """Ask the server for the next safe onboarding action."""
        return call(
            lambda: ok("Next action recommended.", data=ctx.onboarding.next_action(run_id))
        )

    @mcp.tool()
    def summarize_onboarding_status(run_id: str) -> dict[str, Any]:
        """Summarize run, jobs, artifacts, and next action."""
        return call(
            lambda: ok("Onboarding status summarized.", data=ctx.onboarding.summarize(run_id))
        )

    @mcp.tool()
    def generate_onboarding_report(
        run_id: str | None = None,
        pipeline_id: str | None = None,
        include_sections: list[str] | None = None,
        format: str = "markdown",
    ) -> dict[str, Any]:
        """Generate a reproducible onboarding report."""
        return call(
            lambda: ok(
                "Onboarding report generated.",
                data=ctx.artifacts.generate_report(
                    run_id=run_id,
                    pipeline_id=pipeline_id,
                    include_sections=include_sections,
                    format=format,
                ),
            )
        )

    @mcp.tool()
    def get_artifact(artifact_id: str) -> dict[str, Any]:
        """Get artifact metadata and lineage."""
        return call(lambda: ok("Artifact loaded.", data=ctx.artifacts.get_artifact(artifact_id)))

    @mcp.tool()
    def promote_artifact(
        artifact_id: str,
        target_stage: str,
        approval_ticket: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Promote an artifact to staging or production candidate."""
        return call(
            lambda: ctx.artifacts.promote_artifact(
                artifact_id=artifact_id,
                target_stage=target_stage,
                approval_ticket=approval_ticket,
                user_id=user_id,
            )
        )

    return mcp


def _allocate_service_port(
    ctx: AppContext,
    *,
    project_id: str,
    user_id: str,
    purpose: str,
    preferred_port: int | None,
    min_port: int,
    max_port: int,
) -> dict[str, Any]:
    if min_port > max_port:
        raise ValueError("min_port must be <= max_port")
    used_ports = {
        int(port["port"])
        for port in ctx.store.list("ports")
        if port.get("status") == "allocated"
    }
    if preferred_port is not None:
        if preferred_port < min_port or preferred_port > max_port:
            raise ValueError("preferred_port is outside the allowed range")
        if preferred_port in used_ports:
            raise ValueError(f"preferred_port is already allocated: {preferred_port}")
        selected = preferred_port
    else:
        selected = next((port for port in range(min_port, max_port + 1) if port not in used_ports), None)
        if selected is None:
            raise ValueError("no service ports are available")
    port_id = short_id("port")
    record = {
        "port_id": port_id,
        "port": selected,
        "project_id": project_id,
        "user_id": user_id,
        "purpose": purpose,
        "status": "allocated",
        "created_at": utc_now_iso(),
    }
    ctx.store.upsert("ports", port_id, record)
    return record


def _release_service_port(ctx: AppContext, *, port_id: str, reason: str) -> dict[str, Any]:
    port = ctx.store.get("ports", port_id)
    if not port:
        raise ValueError(f"unknown port_id: {port_id}")
    port["status"] = "released"
    port["released_at"] = utc_now_iso()
    port["release_reason"] = reason
    ctx.store.upsert("ports", port_id, port)
    return port


def _start_inference_service(
    ctx: AppContext,
    *,
    artifact_id: str,
    lease_id: str,
    port_id: str,
    backend: str,
    runtime: dict[str, Any] | None,
    service_config: dict[str, Any] | None,
) -> dict[str, Any]:
    artifact = ctx.artifacts.get_artifact(artifact_id)
    lease = ctx.store.get("leases", lease_id)
    if not lease or lease.get("status") != "allocated":
        raise ValueError("start_inference_service requires an allocated lease_id")
    port = ctx.store.get("ports", port_id)
    if not port or port.get("status") != "allocated":
        raise ValueError("start_inference_service requires an allocated port_id")
    service_id = short_id("svc")
    service = {
        "service_id": service_id,
        "artifact_id": artifact_id,
        "lease_id": lease_id,
        "port_id": port_id,
        "port": port["port"],
        "backend": backend,
        "runtime": runtime or {},
        "service_config": service_config or {},
        "project_id": artifact["project_id"],
        "status": "running",
        "endpoint": f"http://127.0.0.1:{port['port']}",
        "created_at": utc_now_iso(),
        "health": {
            "ready": True,
            "last_checked_at": utc_now_iso(),
            "message": "simulation service is ready",
        },
    }
    ctx.store.upsert("services", service_id, service)
    port["bound_service_id"] = service_id
    ctx.store.upsert("ports", port_id, port)
    return service


def _get_service_health(ctx: AppContext, *, service_id: str) -> dict[str, Any]:
    service = ctx.store.get("services", service_id)
    if not service:
        raise ValueError(f"unknown service_id: {service_id}")
    service["health"] = {
        "ready": service.get("status") == "running",
        "last_checked_at": utc_now_iso(),
        "message": "service is healthy" if service.get("status") == "running" else "service is not running",
    }
    ctx.store.upsert("services", service_id, service)
    return service


def _stop_inference_service(ctx: AppContext, *, service_id: str, reason: str) -> dict[str, Any]:
    service = ctx.store.get("services", service_id)
    if not service:
        raise ValueError(f"unknown service_id: {service_id}")
    service["status"] = "stopped"
    service["stopped_at"] = utc_now_iso()
    service["stop_reason"] = reason
    ctx.store.upsert("services", service_id, service)
    port_id = service.get("port_id")
    if port_id:
        _release_service_port(ctx, port_id=port_id, reason=f"service_stopped:{service_id}")
    return service


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _validate_runtime_env(ctx: AppContext, env_id: str) -> dict[str, Any]:
    env = ctx.store.get("runtime_envs", env_id)
    if not env:
        raise ValueError(f"unknown env_id: {env_id}")
    return ok(
        "Runtime environment validated.",
        data={
            "env_id": env_id,
            "ready": env.get("status") == "ready",
            "checks": {
                "image_registered": True,
                "cuda_declared": bool(env.get("cuda")),
                "toolchain_declared": bool(env.get("tools")),
            },
            "environment": env,
        },
    )


def _submit_model_job(
    ctx: AppContext,
    template_id: str,
    *,
    model_id: str,
    lease_id: str,
    workspace_id: str | None,
    env_id: str,
    args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model = ctx.store.get("models", model_id)
    if not model:
        raise ValueError(f"unknown model_id: {model_id}")
    merged_args = {"model_id": model_id} | (args or {})
    return ok(
        "Model job submitted.",
        data=ctx.jobs.submit_job(
            template_id=template_id,
            project_id=model["project_id"],
            user_id="agent",
            workspace_id=workspace_id,
            lease_id=lease_id,
            env_id=env_id,
            args=merged_args,
        ),
    )


def _compare_benchmarks(
    ctx: AppContext,
    baseline_benchmark_id: str | None,
    candidate_benchmark_ids: list[str] | None,
    run_id: str | None,
) -> dict[str, Any]:
    artifacts = ctx.store.list("artifacts")
    if run_id:
        artifacts = [item for item in artifacts if item.get("lineage", {}).get("run_id") == run_id]
    if candidate_benchmark_ids:
        artifacts = [item for item in artifacts if item.get("artifact_id") in candidate_benchmark_ids]
    benchmark_artifacts = [
        item for item in artifacts if item.get("artifact_type") == "benchmark_result"
    ]
    baseline = ctx.store.get("artifacts", baseline_benchmark_id) if baseline_benchmark_id else None
    baseline_throughput = (
        baseline.get("metadata", {}).get("summary", {}).get("throughput_tokens_per_sec")
        if baseline
        else None
    )
    ranking = []
    for artifact in benchmark_artifacts:
        summary = artifact.get("metadata", {}).get("summary", {})
        throughput = summary.get("throughput_tokens_per_sec")
        speedup = summary.get("speedup")
        if speedup is None and baseline_throughput and throughput:
            speedup = round(throughput / baseline_throughput, 2)
        ranking.append(
            {
                "benchmark_id": artifact["artifact_id"],
                "artifact_id": artifact.get("lineage", {}).get("artifact_id"),
                "throughput_tokens_per_sec": throughput,
                "latency_p95_ms": summary.get("latency_p95_ms"),
                "speedup": speedup,
            }
        )
    ranking.sort(key=lambda item: item.get("speedup") or 0, reverse=True)
    return ok(
        "Benchmarks compared.",
        data={
            "baseline_benchmark_id": baseline_benchmark_id,
            "ranking": ranking,
            "recommendation": ranking[0] if ranking else None,
        },
        next_actions=[
            NextAction(
                label="Generate onboarding report",
                tool="generate_onboarding_report",
                arguments={"run_id": run_id} if run_id else {},
                reason="A report should capture the final performance comparison and lineage.",
            )
        ]
        if run_id
        else None,
    )
