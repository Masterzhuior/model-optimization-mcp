"""Built-in catalog data used by local demos and first deployments."""

from __future__ import annotations

from typing import Any

DEFAULT_RUNTIME_ENVS: dict[str, dict[str, Any]] = {
    "llm-opt-cu124-v3": {
        "env_id": "llm-opt-cu124-v3",
        "image": "registry.example.com/ai/llm-opt:cu124-v3",
        "python": "3.11",
        "cuda": "12.4",
        "torch": "2.5",
        "tools": ["vllm", "awq", "gptq", "smoothquant", "tensorrt-llm"],
        "status": "ready",
    },
    "safe-cpu-inspection-v1": {
        "env_id": "safe-cpu-inspection-v1",
        "image": "registry.example.com/ai/model-inspector:latest",
        "python": "3.11",
        "cuda": "none",
        "torch": "cpu",
        "tools": ["safetensors", "transformers", "onnx"],
        "status": "ready",
    },
}


DEFAULT_RECIPES: dict[str, dict[str, Any]] = {
    "recipe-awq-int4-g128": {
        "recipe_id": "recipe-awq-int4-g128",
        "method": "awq",
        "weight_bits": 4,
        "group_size": 128,
        "activation_quant": False,
        "risk": "medium",
        "recommended_for": ["llama", "qwen", "mistral", "baichuan"],
        "expected": {
            "memory_reduction": 0.7,
            "speedup": 2.0,
            "accuracy_drop": 0.008,
        },
    },
    "recipe-gptq-int4-g128": {
        "recipe_id": "recipe-gptq-int4-g128",
        "method": "gptq",
        "weight_bits": 4,
        "group_size": 128,
        "activation_quant": False,
        "risk": "medium",
        "recommended_for": ["llama", "qwen", "mistral"],
        "expected": {
            "memory_reduction": 0.68,
            "speedup": 1.8,
            "accuracy_drop": 0.01,
        },
    },
    "recipe-int8-weight-only": {
        "recipe_id": "recipe-int8-weight-only",
        "method": "int8_weight_only",
        "weight_bits": 8,
        "group_size": None,
        "activation_quant": False,
        "risk": "low",
        "recommended_for": ["llm", "bert", "vision-transformer"],
        "expected": {
            "memory_reduction": 0.45,
            "speedup": 1.35,
            "accuracy_drop": 0.002,
        },
    },
    "recipe-fp8-hopper": {
        "recipe_id": "recipe-fp8-hopper",
        "method": "fp8",
        "weight_bits": 8,
        "activation_quant": True,
        "risk": "medium",
        "recommended_for": ["h100", "h200", "hopper"],
        "expected": {
            "memory_reduction": 0.42,
            "speedup": 1.7,
            "accuracy_drop": 0.004,
        },
    },
}


DEFAULT_DATASETS: dict[str, dict[str, Any]] = {
    "calib-general-v1": {
        "dataset_id": "calib-general-v1",
        "name": "General calibration prompts",
        "usage": ["calibration"],
        "task_type": "text-generation",
        "uri": "dataset://internal/calib-general-v1",
        "sample_count": 10000,
        "sensitivity": "internal",
    },
    "eval-internal-chat-v2": {
        "dataset_id": "eval-internal-chat-v2",
        "name": "Internal chat regression benchmark",
        "usage": ["evaluation"],
        "task_type": "text-generation",
        "uri": "dataset://internal/eval-chat-v2",
        "sample_count": 5000,
        "metrics": ["accuracy", "rouge_l", "exact_match"],
        "sensitivity": "confidential",
    },
}


DEFAULT_TASK_TEMPLATES: dict[str, dict[str, Any]] = {
    "inspect_model_v1": {
        "template_id": "inspect_model_v1",
        "description": "Inspect model files, config, tokenizer, dtype, architecture, and risk flags.",
        "requires_gpu": False,
        "default_duration_seconds": 2,
    },
    "validate_model_load_v1": {
        "template_id": "validate_model_load_v1",
        "description": "Load the model in the target runtime and capture peak memory.",
        "requires_gpu": True,
        "default_duration_seconds": 4,
    },
    "baseline_eval_v1": {
        "template_id": "baseline_eval_v1",
        "description": "Run baseline accuracy evaluation for the original model.",
        "requires_gpu": True,
        "default_duration_seconds": 6,
    },
    "baseline_benchmark_v1": {
        "template_id": "baseline_benchmark_v1",
        "description": "Run latency, throughput, and memory benchmark for the original model.",
        "requires_gpu": True,
        "default_duration_seconds": 6,
    },
    "quantize_model_v1": {
        "template_id": "quantize_model_v1",
        "description": "Run a whitelisted quantization recipe such as AWQ, GPTQ, INT8, or FP8.",
        "requires_gpu": True,
        "default_duration_seconds": 8,
    },
    "quantized_eval_v1": {
        "template_id": "quantized_eval_v1",
        "description": "Evaluate a quantized candidate against an existing baseline.",
        "requires_gpu": True,
        "default_duration_seconds": 6,
    },
    "benchmark_v1": {
        "template_id": "benchmark_v1",
        "description": "Benchmark a model artifact under a serving traffic profile.",
        "requires_gpu": True,
        "default_duration_seconds": 6,
    },
    "profile_v1": {
        "template_id": "profile_v1",
        "description": "Collect profiler traces and summarize GPU bottlenecks.",
        "requires_gpu": True,
        "default_duration_seconds": 6,
    },
    "compile_model_v1": {
        "template_id": "compile_model_v1",
        "description": "Compile or export a model artifact for a target serving backend.",
        "requires_gpu": True,
        "default_duration_seconds": 8,
    },
    "report_v1": {
        "template_id": "report_v1",
        "description": "Generate an onboarding report with lineage and recommendation.",
        "requires_gpu": False,
        "default_duration_seconds": 2,
    },
}

DEFAULT_COMPUTE_POOLS: dict[str, dict[str, Any]] = {
    "gpu-lab-h100": {
        "pool_id": "gpu-lab-h100",
        "name": "Primary H100 optimization pool",
        "region": "cn-shanghai",
        "scheduler": "lease-first",
        "capabilities": ["ptq", "awq", "gptq", "fp8", "vllm", "tensorrt-llm"],
        "default_runtime_env": "llm-opt-cu124-v3",
        "status": "ready",
    },
    "gpu-lab-a100": {
        "pool_id": "gpu-lab-a100",
        "name": "A100 compatibility pool",
        "region": "cn-shanghai",
        "scheduler": "lease-first",
        "capabilities": ["ptq", "awq", "gptq", "smoothquant", "vllm"],
        "default_runtime_env": "llm-opt-cu124-v3",
        "status": "ready",
    },
}


DEFAULT_COMPUTE_NODES: dict[str, dict[str, Any]] = {
    "sim-h100-01": {
        "node_id": "sim-h100-01",
        "pool_id": "gpu-lab-h100",
        "hostname": "sim-h100-01.internal",
        "accelerators": [
            {"uuid": "SIM-H100-0000", "type": "H100", "memory_gb": 80},
            {"uuid": "SIM-H100-0001", "type": "H100", "memory_gb": 80},
        ],
        "cpu_cores": 128,
        "ram_gb": 1024,
        "disk_gb": 8000,
        "status": "ready",
        "last_heartbeat_at": None,
    },
    "sim-a100-01": {
        "node_id": "sim-a100-01",
        "pool_id": "gpu-lab-a100",
        "hostname": "sim-a100-01.internal",
        "accelerators": [
            {"uuid": "SIM-A100-0000", "type": "A100", "memory_gb": 80},
            {"uuid": "SIM-A100-0001", "type": "A100", "memory_gb": 80},
        ],
        "cpu_cores": 96,
        "ram_gb": 768,
        "disk_gb": 6000,
        "status": "ready",
        "last_heartbeat_at": None,
    },
}


DEFAULT_DEVICE_POOLS: dict[str, dict[str, Any]] = {
    "mobile-device-farm-cn": {
        "device_pool_id": "mobile-device-farm-cn",
        "name": "Mobile device farm",
        "region": "cn-shanghai",
        "platforms": ["android"],
        "status": "ready",
        "schedulers": ["matrix", "soak", "regression"],
    }
}


DEFAULT_DEVICES: dict[str, dict[str, Any]] = {
    "android-snapdragon-8gen3-01": {
        "device_id": "android-snapdragon-8gen3-01",
        "device_pool_id": "mobile-device-farm-cn",
        "platform": "android",
        "soc": "snapdragon-8gen3",
        "accelerators": ["cpu", "gpu", "npu"],
        "os_version": "Android 15",
        "memory_gb": 16,
        "status": "ready",
    },
    "android-dimensity-9300-01": {
        "device_id": "android-dimensity-9300-01",
        "device_pool_id": "mobile-device-farm-cn",
        "platform": "android",
        "soc": "dimensity-9300",
        "accelerators": ["cpu", "gpu", "apu"],
        "os_version": "Android 15",
        "memory_gb": 16,
        "status": "ready",
    },
    "android-kirin-9000s-01": {
        "device_id": "android-kirin-9000s-01",
        "device_pool_id": "mobile-device-farm-cn",
        "platform": "android",
        "soc": "kirin-9000s",
        "accelerators": ["cpu", "gpu", "npu"],
        "os_version": "HarmonyOS-compatible Android runtime",
        "memory_gb": 12,
        "status": "ready",
    },
}

DEFAULT_AGENT_SKILLS: dict[str, dict[str, Any]] = {
    "intent-intake": {
        "skill_id": "intent-intake",
        "name": "Intent Intake",
        "executor": "local_skill",
        "description": "Turn a short engineer request into structured intent and clarification questions.",
        "inputs": ["utterance", "project_id", "user_id"],
        "outputs": ["intake_session", "questions", "known_requirements"],
        "mcp_tools": ["start_quantization_intake", "answer_intake_questions"],
    },
    "recipe-authoring": {
        "skill_id": "recipe-authoring",
        "name": "Recipe Authoring",
        "executor": "hybrid",
        "description": "Draft, validate, explain, and revise auditable quantization recipes.",
        "inputs": ["intake_session", "answers"],
        "outputs": ["recipe_spec", "validation", "approval_request"],
        "mcp_tools": ["synthesize_quantization_recipe", "validate_quantization_recipe", "approve_quantization_recipe"],
    },
    "gpu-capacity-planning": {
        "skill_id": "gpu-capacity-planning",
        "name": "GPU Capacity Planning",
        "executor": "mcp_tool",
        "description": "Select compute pools, estimate capacity, and create server-side execution plans.",
        "inputs": ["recipe_id"],
        "outputs": ["compute_pool", "resource_plan", "execution_plan"],
        "mcp_tools": ["list_compute_pools", "select_compute_pool", "create_execution_plan_from_recipe"],
    },
    "ptq-execution": {
        "skill_id": "ptq-execution",
        "name": "PTQ Execution",
        "executor": "mcp_tool",
        "description": "Run approved PTQ candidates on remote GPU workers under leases.",
        "inputs": ["recipe_id", "lease_id"],
        "outputs": ["quantized_artifact", "eval_result", "benchmark_result"],
        "mcp_tools": ["request_resource_lease", "run_quantization", "run_quantized_eval", "run_benchmark"],
    },
    "device-farm-evaluation": {
        "skill_id": "device-farm-evaluation",
        "name": "Device Farm Evaluation",
        "executor": "mcp_tool",
        "description": "Push artifacts to a device farm and collect platform KPI matrices.",
        "inputs": ["artifact_id", "recipe_id", "device_matrix"],
        "outputs": ["device_test_run", "kpi_report"],
        "mcp_tools": ["submit_device_farm_test", "get_device_test_status", "generate_kpi_report"],
    },
    "kpi-regression-analysis": {
        "skill_id": "kpi-regression-analysis",
        "name": "KPI Regression Analysis",
        "executor": "hybrid",
        "description": "Analyze failed accuracy, latency, memory, power, or thermal KPIs and create recipe feedback.",
        "inputs": ["kpi_report_id", "recipe_id"],
        "outputs": ["root_cause", "recipe_feedback", "recipe_revision"],
        "mcp_tools": ["analyze_kpi_regression", "create_recipe_feedback", "create_recipe_revision_from_feedback"],
    },
    "release-reporting": {
        "skill_id": "release-reporting",
        "name": "Release Reporting",
        "executor": "hybrid",
        "description": "Create final onboarding reports and promotion summaries for humans.",
        "inputs": ["run_id", "recipe_id", "kpi_report_id"],
        "outputs": ["report", "promotion_decision"],
        "mcp_tools": ["generate_onboarding_report", "promote_artifact"],
    },
}


def seed_catalog(store: Any) -> None:
    for collection, records in (
        ("runtime_envs", DEFAULT_RUNTIME_ENVS),
        ("recipes", DEFAULT_RECIPES),
        ("datasets", DEFAULT_DATASETS),
        ("task_templates", DEFAULT_TASK_TEMPLATES),
        ("compute_pools", DEFAULT_COMPUTE_POOLS),
        ("compute_nodes", DEFAULT_COMPUTE_NODES),
        ("device_pools", DEFAULT_DEVICE_POOLS),
        ("devices", DEFAULT_DEVICES),
        ("agent_skills", DEFAULT_AGENT_SKILLS),
    ):
        existing = {item.get(f"{collection[:-1]}_id") or item.get("recipe_id") for item in store.list(collection)}
        for item_id, payload in records.items():
            if item_id not in existing and store.get(collection, item_id) is None:
                store.upsert(collection, item_id, payload)
