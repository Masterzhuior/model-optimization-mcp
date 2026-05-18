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


def seed_catalog(store: Any) -> None:
    for collection, records in (
        ("runtime_envs", DEFAULT_RUNTIME_ENVS),
        ("recipes", DEFAULT_RECIPES),
        ("datasets", DEFAULT_DATASETS),
        ("task_templates", DEFAULT_TASK_TEMPLATES),
    ):
        existing = {item.get(f"{collection[:-1]}_id") or item.get("recipe_id") for item in store.list(collection)}
        for item_id, payload in records.items():
            if item_id not in existing and store.get(collection, item_id) is None:
                store.upsert(collection, item_id, payload)

