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
    # v2: Platform-aware conversion and device farm task templates
    "convert_model_mediatek_v1": {
        "template_id": "convert_model_mediatek_v1",
        "description": "Convert model using mtk_converter Python library to TFLite format with PTQ support.",
        "requires_gpu": False,
        "default_duration_seconds": 10,
        "vendor": "mediatek",
        "conversion_type": "mediatek-neuropilot",
    },
    "quantize_model_mediatek_v1": {
        "template_id": "quantize_model_mediatek_v1",
        "description": "Apply quantization using mtk_converter's calibration pipeline (c.quantize=True + c.calibration_data_gen) for INT8/INT4 deployment.",
        "requires_gpu": False,
        "default_duration_seconds": 8,
        "vendor": "mediatek",
        "conversion_type": "mediatek-neuropilot",
    },
    "compile_model_mediatek_v1": {
        "template_id": "compile_model_mediatek_v1",
        "description": "Compile quantized TFLite to DLA format using ncc-tflite for NPU deployment.",
        "requires_gpu": False,
        "default_duration_seconds": 12,
        "vendor": "mediatek",
        "conversion_type": "mediatek-neuropilot",
    },
    "convert_model_qualcomm_v1": {
        "template_id": "convert_model_qualcomm_v1",
        "description": "Convert model using qnn-pytorch-converter or qnn-onnx-converter to QNN IR format.",
        "requires_gpu": False,
        "default_duration_seconds": 10,
        "vendor": "qualcomm",
        "conversion_type": "qualcomm-qnn",
    },
    "compile_model_qualcomm_v1": {
        "template_id": "compile_model_qualcomm_v1",
        "description": "Compile QNN model to context binary for HTP backend.",
        "requires_gpu": False,
        "default_duration_seconds": 12,
        "vendor": "qualcomm",
        "conversion_type": "qualcomm-qnn",
    },
    "deploy_to_device_v1": {
        "template_id": "deploy_to_device_v1",
        "description": "Deploy compiled artifact to device via ADB and validate installation.",
        "requires_gpu": False,
        "default_duration_seconds": 8,
    },
    "run_device_inference_v1": {
        "template_id": "run_device_inference_v1",
        "description": "Run inference on device and collect latency, memory, and power metrics.",
        "requires_gpu": False,
        "default_duration_seconds": 15,
    },
    "collect_device_profile_v1": {
        "template_id": "collect_device_profile_v1",
        "description": "Collect profiling data from device (Neuron Studio / Qualcomm Profiler / ADB).",
        "requires_gpu": False,
        "default_duration_seconds": 10,
    },
    "analyze_conversion_failure_v1": {
        "template_id": "analyze_conversion_failure_v1",
        "description": "Analyze model conversion failure and identify unsupported ops or constraints.",
        "requires_gpu": False,
        "default_duration_seconds": 4,
    },
    "analyze_compile_failure_v1": {
        "template_id": "analyze_compile_failure_v1",
        "description": "Analyze compilation failure and identify hardware constraints.",
        "requires_gpu": False,
        "default_duration_seconds": 4,
    },
    "analyze_runtime_failure_v1": {
        "template_id": "analyze_runtime_failure_v1",
        "description": "Analyze device runtime failure (CPU fallback, crash, execution error).",
        "requires_gpu": False,
        "default_duration_seconds": 4,
    },
    "aws_device_farm_run_v1": {
        "template_id": "aws_device_farm_run_v1",
        "description": "Submit test package to AWS Device Farm and collect device pool results.",
        "requires_gpu": False,
        "default_duration_seconds": 30,
        "platform": "aws-device-farm",
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
    # v2: Platform-aware skills
    "platform-conversion-mediatek": {
        "skill_id": "platform-conversion-mediatek",
        "name": "MediaTek NeuroPilot Conversion",
        "executor": "mcp_tool",
        "description": "Convert, quantize, and compile models for MediaTek NPU deployment using NeuroPilot toolchain.",
        "inputs": ["model_id", "platform_id", "recipe_id"],
        "outputs": ["converted_artifact", "quantized_artifact", "compiled_artifact"],
        "mcp_tools": [
            "convert_model_vendor",
            "quantize_model_vendor",
            "compile_model_vendor",
            "analyze_conversion_failure",
            "analyze_compile_failure",
        ],
        "vendor": "mediatek",
    },
    "platform-conversion-qualcomm": {
        "skill_id": "platform-conversion-qualcomm",
        "name": "Qualcomm QNN Conversion",
        "executor": "mcp_tool",
        "description": "Convert and compile models for Qualcomm Hexagon NPU using AI Engine Direct SDK.",
        "inputs": ["model_id", "platform_id", "recipe_id"],
        "outputs": ["converted_artifact", "compiled_artifact"],
        "mcp_tools": [
            "convert_model_vendor",
            "compile_model_vendor",
            "analyze_conversion_failure",
            "analyze_compile_failure",
        ],
        "vendor": "qualcomm",
    },
    "device-farm-aws": {
        "skill_id": "device-farm-aws",
        "name": "AWS Device Farm Integration",
        "executor": "mcp_tool",
        "description": "Submit artifacts to AWS Device Farm for real-device KPI testing across diverse hardware.",
        "inputs": ["artifact_id", "recipe_id", "device_pool_arn"],
        "outputs": ["device_test_run", "kpi_report"],
        "mcp_tools": [
            "submit_aws_device_farm_test",
            "get_aws_device_farm_test_status",
            "generate_kpi_report",
            "analyze_kpi_regression_detailed",
        ],
        "platform": "aws-device-farm",
    },
    "platform-failure-analysis": {
        "skill_id": "platform-failure-analysis",
        "name": "Platform-Aware Failure Analysis",
        "executor": "hybrid",
        "description": "Analyze conversion, compilation, runtime, and KPI failures with vendor-specific remediation.",
        "inputs": ["failure_phase", "artifact_id", "kpi_report_id"],
        "outputs": ["failure_analysis", "recipe_feedback", "recipe_revision"],
        "mcp_tools": [
            "analyze_conversion_failure",
            "analyze_compile_failure",
            "analyze_runtime_failure",
            "analyze_kpi_regression_detailed",
            "create_recipe_feedback",
            "create_recipe_revision_from_feedback",
        ],
    },
    "platform-profiling": {
        "skill_id": "platform-profiling",
        "name": "Device Profiling",
        "executor": "mcp_tool",
        "description": "Collect and analyze profiling data from devices (Neuron Studio / Qualcomm Profiler / ADB).",
        "inputs": ["artifact_id", "device_id"],
        "outputs": ["profile_artifact", "bottlenecks", "recommendations"],
        "mcp_tools": [
            "collect_device_profile",
            "analyze_profile",
            "get_profile_recommendations",
        ],
    },
}


# v2: Platform profiles for MediaTek and Qualcomm
DEFAULT_PLATFORM_PROFILES: dict[str, dict[str, Any]] = {
    "mediatek-dimensity-9400": {
        "platform_id": "mediatek-dimensity-9400",
        "vendor": "mediatek",
        "product_line": "dimensity",
        "soc": "dimensity-9400",
        "soc_codename": "mt6991",
        "accelerators": [
            {"type": "npu", "name": "APU 790", "tops": 46, "memory_gb": 4},
            {"type": "gpu", "name": "Mali-G720", "cores": 12, "memory_gb": 4},
        ],
        "npu_version": "NP8",
        "mdla_version": "5.3",
        "os_options": ["android-14", "android-15"],
        "runtime_options": ["neuron-runtime", "tflite-delegate", "nnapi-delegate"],
        "inference_paths": ["online", "offline"],
        "sdk_bundles": [
            {
                "name": "neuropilot-sdk",
                "version": "4.2.1",
                "download_url": "https://neuropilot.mediatek.io/sdk",
            }
        ],
        "converter": "mtk_converter",
        "compiler": "ncc-tflite",
        "profiler": "neuron-studio",
        "supported_ops": [
            "Conv2D", "DepthwiseConv2D", "ConvTranspose2D",
            "MatMul", "BatchMatMul", "FullyConnected",
            "ReLU", "ReLU6", "LeakyReLU", "PReLU",
            "Sigmoid", "Tanh", "Swish", "GELU", "SiLU",
            "Softmax", "LogSoftmax",
            "BatchNorm", "LayerNorm", "RMSNorm", "InstanceNorm",
            "MaxPool", "AveragePool", "GlobalAveragePool",
            "Add", "Sub", "Mul", "Div", "Pow",
            "Reshape", "Transpose", "Concat", "Split",
            "Gather", "Scatter", "Slice", "Pad",
        ],
        "quantization_schemes": ["int8", "int4", "mixed", "fp16"],
        "max_model_size_gb": 4.0,
        "max_context_length": 32768,
        "known_limitations": [
            "Custom ops require NPU compiler support",
            "FP16 models must be quantized for NPU",
            "Dynamic shapes have limited NPU support",
        ],
        "workarounds": {
            "custom_ops": "Replace with supported ops or enable CPU fallback",
            "fp16": "Apply PTQ with INT8 quantization",
            "dynamic_shapes": "Use static shapes or split into fixed-shape variants",
        },
        "documentation_url": "https://neuropilot.mediatek.io/docs",
        "sdk_download_url": "https://neuropilot.mediatek.io/sdk",
        "status": "active",
    },
    "mediatek-dimensity-9300": {
        "platform_id": "mediatek-dimensity-9300",
        "vendor": "mediatek",
        "product_line": "dimensity",
        "soc": "dimensity-9300",
        "soc_codename": "mt6989",
        "accelerators": [
            {"type": "npu", "name": "APU 780", "tops": 36, "memory_gb": 4},
            {"type": "gpu", "name": "Mali-G720", "cores": 10, "memory_gb": 4},
        ],
        "npu_version": "NP7",
        "mdla_version": "5.2",
        "os_options": ["android-14"],
        "runtime_options": ["neuron-runtime", "tflite-delegate", "nnapi-delegate"],
        "inference_paths": ["online", "offline"],
        "sdk_bundles": [
            {
                "name": "neuropilot-sdk",
                "version": "4.1.0",
                "download_url": "https://neuropilot.mediatek.io/sdk",
            }
        ],
        "converter": "mtk_converter",
        "compiler": "ncc-tflite",
        "profiler": "neuron-studio",
        "supported_ops": [
            "Conv2D", "DepthwiseConv2D",
            "MatMul", "BatchMatMul", "FullyConnected",
            "ReLU", "ReLU6", "LeakyReLU",
            "Sigmoid", "Tanh", "Swish", "GELU", "SiLU",
            "Softmax",
            "BatchNorm", "LayerNorm", "RMSNorm",
            "MaxPool", "AveragePool", "GlobalAveragePool",
            "Add", "Sub", "Mul", "Div",
            "Reshape", "Transpose", "Concat", "Split",
            "Gather", "Slice", "Pad",
        ],
        "quantization_schemes": ["int8", "int4", "mixed"],
        "max_model_size_gb": 3.0,
        "max_context_length": 16384,
        "sdk_access_tier": "basic",
        "sdk_download_note": "Genio platforms may require separate mt8189 package download from NeuroPilot portal",
        "known_limitations": [
            "ConvTranspose2D not supported on NPU",
            "PReLU not supported on NPU",
            "LogSoftmax not supported on NPU",
        ],
        "workarounds": {
            "convtranspose": "Use CPU fallback or replace with equivalent ops",
            "prelu": "Replace with ReLU or LeakyReLU",
        },
        "documentation_url": "https://neuropilot.mediatek.io/docs",
        "status": "active",
    },
    "qualcomm-snapdragon-8gen3": {
        "platform_id": "qualcomm-snapdragon-8gen3",
        "vendor": "qualcomm",
        "product_line": "snapdragon",
        "soc": "snapdragon-8gen3",
        "accelerators": [
            {"type": "npu", "name": "Hexagon NPU", "tops": 73, "memory_gb": 4},
            {"type": "gpu", "name": "Adreno 750", "cores": 1, "memory_gb": 4},
        ],
        "npu_version": "v75",
        "mdla_version": None,
        "os_options": ["android-14"],
        "runtime_options": ["qnn", "tflite-delegate", "snpe"],
        "inference_paths": ["online", "offline"],
        "sdk_bundles": [
            {
                "name": "qualcomm-ai-engine-direct",
                "version": "2.22.0",
                "download_url": "https://www.qualcomm.com/developer/software/qualcomm-ai-engine-direct",
            }
        ],
        "soc_codename": "sm8650",
        "converter": "qnn-pytorch-converter",
        "converter_onnx": "qnn-onnx-converter",
        "compiler": "qnn-context-binary-generator",
        "profiler": "qualcomm-profiling-tools",
        "supported_ops": [
            "Conv2D", "DepthwiseConv2D", "ConvTranspose2D",
            "MatMul", "BatchMatMul", "FullyConnected",
            "ReLU", "ReLU6", "LeakyReLU", "PReLU",
            "Sigmoid", "Tanh", "Swish", "GELU", "SiLU",
            "Softmax", "LogSoftmax",
            "BatchNorm", "LayerNorm", "RMSNorm", "InstanceNorm", "GroupNorm",
            "MaxPool", "AveragePool", "GlobalAveragePool",
            "Add", "Sub", "Mul", "Div", "Pow",
            "Abs", "Neg", "Exp", "Log", "Sqrt",
            "ReduceSum", "ReduceMean", "ReduceMax", "ReduceMin",
            "Reshape", "Transpose", "Concat", "Split",
            "Gather", "Scatter", "Slice", "Pad",
        ],
        "quantization_schemes": ["int8", "int16", "float16"],
        "max_model_size_gb": 4.0,
        "max_context_length": 32768,
        "htp_performance_modes": [
            "burst", "sustained_high_performance", "high_performance",
            "balanced", "default", "low_balanced",
            "power_saver", "high_power_saver", "low_power_saver",
        ],
        "known_limitations": [
            "Some custom layers need HTP support",
            "INT4 requires careful calibration",
            "Context binary generation supported only on Linux hosts",
        ],
        "workarounds": {
            "custom_layers": "Use QNN compatibility checker (qnn-onnx-converter --dry_run) before compilation",
            "int4_calibration": "Use mixed precision with INT8 for sensitive layers",
            "windows_context": "Generate context binary on Linux, deploy .serialized to Windows",
        },
        "documentation_url": "https://developer.qualcomm.com/software/qualcomm-ai-engine-direct",
        "status": "active",
    },
    "qualcomm-snapdragon-8gen2": {
        "platform_id": "qualcomm-snapdragon-8gen2",
        "vendor": "qualcomm",
        "product_line": "snapdragon",
        "soc": "snapdragon-8gen2",
        "accelerators": [
            {"type": "npu", "name": "Hexagon NPU", "tops": 48, "memory_gb": 4},
            {"type": "gpu", "name": "Adreno 740", "cores": 1, "memory_gb": 4},
        ],
        "npu_version": "v73",
        "mdla_version": None,
        "os_options": ["android-13", "android-14"],
        "runtime_options": ["qnn", "tflite-delegate", "snpe"],
        "inference_paths": ["online", "offline"],
        "sdk_bundles": [
            {
                "name": "qualcomm-ai-engine-direct",
                "version": "2.20.0",
                "download_url": "https://www.qualcomm.com/developer/software/qualcomm-ai-engine-direct",
            }
        ],
        "soc_codename": "sm8550",
        "converter": "qnn-pytorch-converter",
        "converter_onnx": "qnn-onnx-converter",
        "compiler": "qnn-context-binary-generator",
        "profiler": "qualcomm-profiling-tools",
        "supported_ops": [
            "Conv2D", "DepthwiseConv2D",
            "MatMul", "BatchMatMul", "FullyConnected",
            "ReLU", "ReLU6", "LeakyReLU",
            "Sigmoid", "Tanh", "Swish", "GELU", "SiLU",
            "Softmax",
            "BatchNorm", "LayerNorm",
            "MaxPool", "AveragePool", "GlobalAveragePool",
            "Add", "Sub", "Mul", "Div",
            "Reshape", "Transpose", "Concat", "Split",
            "Gather", "Slice", "Pad",
        ],
        "quantization_schemes": ["int8", "int16", "float16"],
        "max_model_size_gb": 3.0,
        "max_context_length": 16384,
        "htp_performance_modes": [
            "burst", "sustained_high_performance", "high_performance",
            "balanced", "default", "low_balanced",
            "power_saver", "high_power_saver", "low_power_saver",
        ],
        "known_limitations": [
            "GroupNorm not supported on HTP",
            "Reduce ops have limited support",
        ],
        "workarounds": {
            "groupnorm": "Replace with BatchNorm or LayerNorm",
            "reduce_ops": "Decompose into supported ops",
        },
        "documentation_url": "https://developer.qualcomm.com/software/qualcomm-ai-engine-direct",
        "status": "active",
    },
}


# v2: Vendor adapter registry
DEFAULT_VENDOR_ADAPTERS: dict[str, dict[str, Any]] = {
    "mediatek-neuropilot": {
        "adapter_id": "mediatek-neuropilot",
        "vendor": "mediatek",
        "name": "MediaTek NeuroPilot Adapter",
        "description": "Adapter for MediaTek NeuroPilot SDK - converts, quantizes, and compiles models for NPU deployment.",
        "supported_platforms": ["mediatek-dimensity-9400", "mediatek-dimensity-9300"],
        "conversion_pipeline": [
            {
                "step": "convert",
                "tool": "mtk_converter",
                "cli": "python3 -c \"import mtk_converter; c=mtk_converter.PyTorchConverter.from_script_module_file('model.torchscript', input_shapes=[(1,3,640,640)]); c.quantize=True; c.calibration_data_gen=gen; c.convert_to_tflite('model.tflite')\"",
                "optional_flags": ["c.quantize=False for FP32 (no quantization)"],
                "input": "pytorch (TorchScript .torchscript)",
                "output": "tflite",
                "note": "mtk_converter is a Python library (pip install); PTQ via c.quantize=True + c.calibration_data_gen",
                "package": "mtk_converter",
            },
            {
                "step": "compile",
                "tool": "ncc-tflite",
                "cli": "ncc-tflite --arch=mdla3.0 model.tflite -o model.dla",
                "optional_flags": ["--relax-fp32  (for FP32→FP16 on NPU)", "--opt-bw  (optimize bandwidth)"],
                "input": "quantized-tflite",
                "output": "dla",
                "note": "ncc-tflite binary is SoC-specific (mt6991/, mt8189/ etc.); --arch specifies MDLA version",
            },
        ],
        "runtime_tool": "neuronrt",
        "runtime_cli": "adb shell \"neuronrt -m hw -a model.dla -i input.bin -c 10\"",
        "runtime_note": "neuronrt runs on-device for verification; -m hw = hardware, -c count = benchmark repeats; for production use Neuron Runtime API",
        "profiling_tool": "neuron-studio",
        "profiling_metrics": ["npu_frequency", "npu_loading", "dram_utilization", "cpu_fallback_count"],
        "failure_handlers": {
            "conversion": "analyze_conversion_failure",
            "compile": "analyze_compile_failure",
            "runtime": "analyze_runtime_failure",
        },
        "status": "active",
    },
    "qualcomm-qnn": {
        "adapter_id": "qualcomm-qnn",
        "vendor": "qualcomm",
        "name": "Qualcomm AI Engine Direct Adapter",
        "description": "Adapter for Qualcomm QNN SDK - converts and compiles models for Hexagon NPU.",
        "supported_platforms": ["qualcomm-snapdragon-8gen3", "qualcomm-snapdragon-8gen2"],
        "conversion_pipeline": [
            {
                "step": "convert_pytorch",
                "tool": "qnn-pytorch-converter",
                "cli": "qnn-pytorch-converter --input_network model.pt --input_dim 'input' 1,3,224,224 --output_path model.cpp",
                "input": "pytorch (TorchScript .pt)",
                "output": "qnn-model (.cpp/.so)",
                "note": "Requires --input_dim for each input tensor",
            },
            {
                "step": "convert_onnx",
                "tool": "qnn-onnx-converter",
                "cli": "qnn-onnx-converter --input_network model.onnx --output_path model.cpp",
                "optional_flags": ["--dry_run  (analyze unsupported ops)"],
                "input": "onnx (opset <= 24)",
                "output": "qnn-model",
                "note": "Auto-runs onnx-simplifier unless custom ops/quant overrides provided",
            },
            {
                "step": "compile",
                "tool": "qnn-context-binary-generator",
                "cli": "qnn-context-binary-generator --backend libQnnHtp.so --model model.so --config_file htp_config.json --binary_file output.serialized",
                "input": "qnn-model + config",
                "output": "context-binary (.serialized)",
                "note": "Context binary generation supported only on Linux hosts",
            },
        ],
        "profiling_tool": "qualcomm-profiling-tools",
        "profiling_metrics": ["htp_utilization", "memory_bandwidth", "cpu_fallback_count"],
        "failure_handlers": {
            "conversion": "analyze_conversion_failure",
            "compile": "analyze_compile_failure",
            "runtime": "analyze_runtime_failure",
        },
        "status": "active",
    },
    "aws-device-farm": {
        "adapter_id": "aws-device-farm",
        "vendor": "aws",
        "name": "AWS Device Farm Adapter",
        "description": "Adapter for AWS Device Farm - manages device pools, test submissions, and KPI collection.",
        "supported_platforms": ["android", "ios"],
        "conversion_pipeline": [],
        "profiling_tool": "adb-profiling",
        "profiling_metrics": ["latency", "memory", "power", "thermal"],
        "failure_handlers": {
            "runtime": "analyze_runtime_failure",
            "kpi": "analyze_kpi_regression_detailed",
        },
        "status": "active",
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
        # v2: Platform-aware collections
        ("platform_profiles", DEFAULT_PLATFORM_PROFILES),
        ("vendor_adapters", DEFAULT_VENDOR_ADAPTERS),
    ):
        existing = {
            item.get(f"{collection[:-1]}_id")
            or item.get(f"{collection[:-2]}_id")
            or item.get("recipe_id")
            or item.get("platform_id")
            or item.get("adapter_id")
            for item in store.list(collection)
        }
        for item_id, payload in records.items():
            if item_id not in existing and store.get(collection, item_id) is None:
                store.upsert(collection, item_id, payload)
