# Model Optimization MCP v2: Comprehensive Design

**Date**: 2026-05-29  
**Status**: Draft  
**Author**: Sisyphus (analysis synthesis)

---

## Executive Summary

This document presents a comprehensive redesign of the Model Optimization MCP platform, addressing gaps identified in the current implementation and incorporating industry patterns from NVIDIA, MediaTek, Qualcomm, Apple, and production device farm architectures.

**Key Design Goals:**
1. **Platform-Aware Recipes** - Recipes as deployment contracts, not just quantization configs
2. **Vendor Adapter Architecture** - Pluggable vendor support (NVIDIA, MediaTek, Qualcomm, Apple)
3. **Stage-Aware Failure Analysis** - Granular failure classification across conversion/compile/runtime/KPI stages
4. **Profiling-First Feedback** - Integrate trace data into KPI regression analysis
5. **Production-Grade State** - Migration path from JSON to Postgres/Redis
6. **Multi-Tenant Security** - SSO/RBAC/quota enforcement

---

## 1. Architecture Overview

### 1.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Agent Layer (Local)                          │
│  Claude Code / Codex / Cursor + Skill Pack                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MCP Protocol
┌──────────────────────────▼──────────────────────────────────────┐
│                     Gateway Layer                                │
│  Auth (SSO/RBAC) · Rate Limiting · Request Routing              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Control Plane (MCP Server)                   │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ Recipe      │ │ Compute      │ │ Device Farm  │             │
│  │ Registry    │ │ Control      │ │ Manager      │             │
│  ├─────────────┤ ├──────────────┤ ├──────────────┤             │
│  │ Artifact    │ │ Resource     │ │ KPI          │             │
│  │ Lineage     │ │ Governance   │ │ Analytics    │             │
│  └─────────────┘ └──────────────┘ └──────────────┘             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Adapter Layer (Vendor-Specific)              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │
│  │ NVIDIA     │ │ MediaTek   │ │ Qualcomm   │ │ Apple      │  │
│  │ TensorRT   │ │ NeuroPilot │ │ QNN        │ │ CoreML     │  │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Execution Layer                              │
│  GPU Workers · Device Farm · Object Storage · Message Queue     │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Core Design Principles

1. **Recipe as Contract** - A recipe is a platform-specific deployment contract, not just a quantization config
2. **Adapter Pattern** - Vendor-specific logic lives in adapters, not core MCP
3. **Stage-Aware Pipeline** - Every pipeline stage (convert/compile/runtime/KPI) has explicit failure handling
4. **Trace-First Observability** - Profiling traces are first-class artifacts linked to KPI reports
5. **Local Skills for Reasoning** - MCP owns state; skills own reasoning and explanation

---

## 2. Platform Profile Registry

### 2.1 Purpose

Define a first-class registry for target platforms, enabling platform-aware recipe generation, validation, and device matrix selection.

### 2.2 Schema

```python
@dataclass
class PlatformProfile:
    """Platform-specific hardware and SDK configuration."""
    
    platform_id: str                    # "mediatek-dimensity-9400"
    vendor: str                         # "mediatek"
    product_line: str                   # "dimensity" | "genio"
    soc: str                            # "dimensity-9400"
    
    # Hardware
    accelerators: list[AcceleratorSpec] # NPU, GPU, CPU
    npu_version: str | None             # "NP8"
    mdla_version: str | None            # "5.3"
    
    # Software Stack
    os_options: list[str]               # ["android-14", "yocto", "ubuntu"]
    runtime_options: list[str]          # ["neuron-runtime", "tflite", "onnxruntime"]
    inference_paths: list[str]          # ["online", "offline"]
    
    # SDK/Toolchain
    sdk_bundles: list[SDKBundle]        # [{name, version, download_url}]
    converter: str | None               # "np-converter"
    compiler: str | None                # "ncc-tflite"
    profiler: str | None                # "neuron-studio"
    
    # Capabilities
    supported_ops: list[str]            # ["Conv2D", "MatMul", "LayerNorm", ...]
    quantization_schemes: list[str]     # ["int8", "int4", "mixed"]
    max_model_size_gb: float
    max_context_length: int
    
    # Known Issues
    known_limitations: list[str]
    workarounds: dict[str, str]
    
    # Metadata
    documentation_url: str | None
    sdk_download_url: str | None
    status: str                         # "active" | "deprecated" | "experimental"
```

### 2.3 Example Profiles

```json
{
  "platform_id": "mediatek-dimensity-9400",
  "vendor": "mediatek",
  "product_line": "dimensity",
  "soc": "dimensity-9400",
  "accelerators": [
    {"type": "npu", "name": "APU 790", "tops": 46},
    {"type": "gpu", "name": "Mali-G720", "cores": 12}
  ],
  "npu_version": "NP8",
  "mdla_version": "5.3",
  "os_options": ["android-14", "android-15"],
  "runtime_options": ["neuron-runtime", "tflite-delegate"],
  "inference_paths": ["online", "offline"],
  "sdk_bundles": [
    {
      "name": "neuropilot-sdk",
      "version": "4.2.1",
      "download_url": "https://neuropilot.mediatek.io/sdk"
    }
  ],
  "converter": "np-converter",
  "compiler": "ncc-tflite",
  "profiler": "neuron-studio",
  "supported_ops": [
    "Conv2D", "DepthwiseConv2D", "MatMul", "BatchMatMul",
    "LayerNorm", "RMSNorm", "Softmax", "GELU", "SiLU",
    "Add", "Mul", "Reshape", "Transpose", "Gather"
  ],
  "quantization_schemes": ["int8", "int4", "mixed"],
  "max_model_size_gb": 4.0,
  "max_context_length": 32768,
  "known_limitations": [
    "Custom ops require NPU compiler support",
    "FP16 models must be quantized for NPU"
  ],
  "documentation_url": "https://neuropilot.mediatek.io/docs",
  "status": "active"
}
```

```json
{
  "platform_id": "qualcomm-snapdragon-8gen3",
  "vendor": "qualcomm",
  "product_line": "snapdragon",
  "soc": "snapdragon-8gen3",
  "accelerators": [
    {"type": "npu", "name": "Hexagon NPU", "tops": 73},
    {"type": "gpu", "name": "Adreno 750", "cores": 1}
  ],
  "npu_version": "v75",
  "mdla_version": null,
  "os_options": ["android-14"],
  "runtime_options": ["qnn", "tflite-delegate", "snpe"],
  "inference_paths": ["online", "offline"],
  "sdk_bundles": [
    {
      "name": "qualcomm-ai-engine-direct",
      "version": "2.22.0",
      "download_url": "https://www.qualcomm.com/developer/software/qualcomm-ai-engine-direct"
    }
  ],
  "converter": "qnn-converter",
  "compiler": "qnn-context-binary-generator",
  "profiler": "qualcomm-profiling-tools",
  "supported_ops": [
    "Conv2D", "DepthwiseConv2D", "MatMul", "BatchMatMul",
    "LayerNorm", "RMSNorm", "Softmax", "GELU", "SiLU",
    "Add", "Mul", "Reshape", "Transpose", "Gather", "Slice"
  ],
  "quantization_schemes": ["int8", "int16", "float16"],
  "max_model_size_gb": 4.0,
  "max_context_length": 32768,
  "documentation_url": "https://developer.qualcomm.com/software/qualcomm-ai-engine-direct",
  "status": "active"
}
```

```json
{
  "platform_id": "apple-m4",
  "vendor": "apple",
  "product_line": "m-series",
  "soc": "m4",
  "accelerators": [
    {"type": "ane", "name": "Neural Engine", "tops": 38},
    {"type": "gpu", "name": "Apple GPU", "cores": 10}
  ],
  "npu_version": null,
  "mdla_version": null,
  "os_options": ["ios-17", "ipados-17", "macos-14"],
  "runtime_options": ["coreml", "mps"],
  "inference_paths": ["online"],
  "sdk_bundles": [
    {
      "name": "coremltools",
      "version": "8.0",
      "download_url": "https://github.com/apple/coremltools"
    }
  ],
  "converter": "coremltools",
  "compiler": "coremltools",
  "profiler": "xcode-instruments",
  "supported_ops": [
    "Conv2D", "DepthwiseConv2D", "MatMul", "BatchMatMul",
    "LayerNorm", "RMSNorm", "Softmax", "GELU", "SiLU",
    "Add", "Mul", "Reshape", "Transpose", "Gather"
  ],
  "quantization_schemes": ["int8", "float16", "coreml-compressed"],
  "max_model_size_gb": 4.0,
  "max_context_length": 32768,
  "documentation_url": "https://developer.apple.com/documentation/coreml",
  "status": "active"
}
```

### 2.4 MCP Tools for Platform Registry

```python
@mcp.tool()
def list_platform_profiles(
    vendor: str | None = None,
    product_line: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """List available platform profiles."""

@mcp.tool()
def get_platform_profile(platform_id: str) -> dict[str, Any]:
    """Get detailed platform profile."""

@mcp.tool()
def check_op_compatibility(
    platform_id: str,
    ops: list[str],
) -> dict[str, Any]:
    """Check if a list of ops is supported on a platform."""

@mcp.tool()
def get_platform_quantization_options(
    platform_id: str,
) -> dict[str, Any]:
    """Get supported quantization schemes for a platform."""
```

---

## 3. Vendor Adapter Architecture

### 3.1 Abstract Adapter Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ConversionResult:
    """Result of a model conversion step."""
    success: bool
    artifact_path: str | None
    converted_ops: list[str]
    unsupported_ops: list[str]
    warnings: list[str]
    metadata: dict[str, Any]


@dataclass
class CompilationResult:
    """Result of a model compilation step."""
    success: bool
    compiled_artifact_path: str | None
    binary_format: str
    size_gb: float
    warnings: list[str]
    metadata: dict[str, Any]


@dataclass
class DeviceKPI:
    """KPI measurement from a device."""
    device_id: str
    platform_id: str
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float | None
    memory_peak_mb: int
    power_mw: int | None
    thermal_c: float | None
    npu_loading_percent: float | None
    cpu_fallback_count: int
    unsupported_op_count: int
    tokens_per_second: float | None
    first_token_latency_ms: float | None
    raw_metrics: dict[str, Any]


class VendorAdapter(ABC):
    """Abstract base class for vendor-specific adapters."""
    
    @property
    @abstractmethod
    def vendor_id(self) -> str:
        """Vendor identifier (e.g., 'nvidia', 'mediatek', 'qualcomm', 'apple')."""
    
    @property
    @abstractmethod
    def supported_platforms(self) -> list[str]:
        """List of platform_ids this adapter supports."""
    
    @abstractmethod
    def inspect_platform(self, device_id: str) -> dict[str, Any]:
        """Inspect a connected device's platform capabilities."""
    
    @abstractmethod
    def convert_model(
        self,
        model_path: str,
        platform_id: str,
        conversion_config: dict[str, Any],
    ) -> ConversionResult:
        """Convert a model to the vendor's intermediate format."""
    
    @abstractmethod
    def quantize_model(
        self,
        converted_model_path: str,
        platform_id: str,
        quantization_config: dict[str, Any],
    ) -> ConversionResult:
        """Quantize a converted model."""
    
    @abstractmethod
    def compile_model(
        self,
        quantized_model_path: str,
        platform_id: str,
        compilation_config: dict[str, Any],
    ) -> CompilationResult:
        """Compile a quantized model for device deployment."""
    
    @abstractmethod
    def deploy_artifact(
        self,
        compiled_artifact_path: str,
        device_id: str,
    ) -> dict[str, Any]:
        """Deploy a compiled artifact to a device."""
    
    @abstractmethod
    def run_inference(
        self,
        artifact_path: str,
        device_id: str,
        inference_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Run inference on a device and return results."""
    
    @abstractmethod
    def collect_profile(
        self,
        device_id: str,
        profile_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Collect profiling data from a device."""
    
    @abstractmethod
    def analyze_failure(
        self,
        failure_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze a failure and suggest remediation."""
    
    @abstractmethod
    def get_supported_ops(self, platform_id: str) -> list[str]:
        """Get list of supported ops for a platform."""
    
    @abstractmethod
    def get_quantization_schemes(self, platform_id: str) -> list[str]:
        """Get supported quantization schemes for a platform."""
```

### 3.2 NVIDIA TensorRT Adapter

```python
class NVIDIATensorRTAdapter(VendorAdapter):
    """NVIDIA TensorRT/TensorRT-LLM adapter."""
    
    @property
    def vendor_id(self) -> str:
        return "nvidia"
    
    @property
    def supported_platforms(self) -> list[str]:
        return ["nvidia-h100", "nvidia-a100", "nvidia-l4", "nvidia-orin"]
    
    def convert_model(
        self,
        model_path: str,
        platform_id: str,
        conversion_config: dict[str, Any],
    ) -> ConversionResult:
        """
        Convert model to TensorRT-LLM format.
        
        Pipeline:
        1. Load HuggingFace model
        2. Apply quantization (AWQ/GPTQ/SmoothQuant)
        3. Build TensorRT engine
        4. Generate config.json
        """
        # Implementation would call tensorrt_llm APIs
        pass
    
    def compile_model(
        self,
        quantized_model_path: str,
        platform_id: str,
        compilation_config: dict[str, Any],
    ) -> CompilationResult:
        """
        Compile TensorRT engine for target GPU.
        
        Steps:
        1. Read quantized model
        2. Set optimization profiles
        3. Build engine with target precision
        4. Validate engine
        """
        pass
    
    def collect_profile(
        self,
        device_id: str,
        profile_config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Collect NVIDIA Nsight Systems profile.
        
        Metrics:
        - GPU utilization
        - Kernel execution times
        - Memory bandwidth usage
        - CUDA API calls
        - NVTX markers
        """
        pass
```

### 3.3 MediaTek NeuroPilot Adapter

```python
class MediaTekNeuroPilotAdapter(VendorAdapter):
    """MediaTek NeuroPilot/Neuron SDK adapter."""
    
    @property
    def vendor_id(self) -> str:
        return "mediatek"
    
    @property
    def supported_platforms(self) -> list[str]:
        return [
            "mediatek-dimensity-9400",
            "mediatek-dimensity-9300",
            "mediatek-genio-720",
            "mediatek-genio-510",
        ]
    
    def convert_model(
        self,
        model_path: str,
        platform_id: str,
        conversion_config: dict[str, Any],
    ) -> ConversionResult:
        """
        Convert model using np-converter.
        
        Pipeline:
        1. Load PyTorch/ONNX model
        2. Run np-converter to TFLite
        3. Check op compatibility
        4. Report unsupported ops
        """
        pass
    
    def quantize_model(
        self,
        converted_model_path: str,
        platform_id: str,
        quantization_config: dict[str, Any],
    ) -> ConversionResult:
        """
        Apply post-training quantization.
        
        Steps:
        1. Load TFLite model
        2. Run PTQ with calibration data
        3. Generate INT8 quantized model
        4. Validate accuracy
        """
        pass
    
    def compile_model(
        self,
        quantized_model_path: str,
        platform_id: str,
        compilation_config: dict[str, Any],
    ) -> CompilationResult:
        """
        Compile to DLA format using ncc-tflite.
        
        Steps:
        1. Load quantized TFLite
        2. Compile with ncc-tflite
        3. Generate .dla binary
        4. Validate binary
        """
        pass
    
    def collect_profile(
        self,
        device_id: str,
        profile_config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Collect Neuron Studio profile.
        
        Metrics:
        - NPU frequency and loading
        - DRAM utilization
        - Workflow traces
        - CPU fallback count
        """
        pass
    
    def analyze_failure(
        self,
        failure_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Analyze MediaTek-specific failures.
        
        Failure phases:
        - conversion: np-converter limitations
        - compile: ncc-tflite hardware constraints
        - runtime: neuron-runtime fallback
        - kpi: accuracy/latency regression
        """
        pass
```

### 3.4 Qualcomm QNN Adapter

```python
class QualcommQNNAdapter(VendorAdapter):
    """Qualcomm AI Engine Direct / QNN adapter."""
    
    @property
    def vendor_id(self) -> str:
        return "qualcomm"
    
    @property
    def supported_platforms(self) -> list[str]:
        return [
            "qualcomm-snapdragon-8gen3",
            "qualcomm-snapdragon-8gen2",
            "qualcomm-snapdragon-7gen1",
        ]
    
    def convert_model(
        self,
        model_path: str,
        platform_id: str,
        conversion_config: dict[str, Any],
    ) -> ConversionResult:
        """
        Convert model using QNN converter.
        
        Pipeline:
        1. Load PyTorch/ONNX model
        2. Run qnn-converter
        3. Generate QNN context
        """
        pass
    
    def compile_model(
        self,
        quantized_model_path: str,
        platform_id: str,
        compilation_config: dict[str, Any],
    ) -> CompilationResult:
        """
        Compile to QNN context binary.
        
        Steps:
        1. Load QNN model
        2. Set HTP backend options
        3. Generate context binary
        """
        pass
```

### 3.5 Apple CoreML Adapter

```python
class AppleCoreMLAdapter(VendorAdapter):
    """Apple CoreML / Neural Engine adapter."""
    
    @property
    def vendor_id(self) -> str:
        return "apple"
    
    @property
    def supported_platforms(self) -> list[str]:
        return ["apple-m4", "apple-m3", "apple-a17", "apple-a16"]
    
    def convert_model(
        self,
        model_path: str,
        platform_id: str,
        conversion_config: dict[str, Any],
    ) -> ConversionResult:
        """
        Convert model using coremltools.
        
        Pipeline:
        1. Load PyTorch model
        2. Trace/export to CoreML format
        3. Apply optimizations
        """
        pass
    
    def compile_model(
        self,
        quantized_model_path: str,
        platform_id: str,
        compilation_config: dict[str, Any],
    ) -> CompilationResult:
        """
        Compile CoreML model for Neural Engine.
        
        Steps:
        1. Load CoreML model
        2. Set compute units (ANE/GPU/CPU)
        3. Compile for target device
        """
        pass
```

### 3.6 Adapter Registry

```python
class AdapterRegistry:
    """Registry for vendor adapters."""
    
    def __init__(self):
        self._adapters: dict[str, VendorAdapter] = {}
    
    def register(self, adapter: VendorAdapter) -> None:
        """Register a vendor adapter."""
        self._adapters[adapter.vendor_id] = adapter
    
    def get_adapter(self, vendor_id: str) -> VendorAdapter | None:
        """Get adapter by vendor ID."""
        return self._adapters.get(vendor_id)
    
    def get_adapter_for_platform(self, platform_id: str) -> VendorAdapter | None:
        """Get adapter that supports a given platform."""
        for adapter in self._adapters.values():
            if platform_id in adapter.supported_platforms:
                return adapter
        return None
    
    def list_adapters(self) -> list[dict[str, Any]]:
        """List all registered adapters."""
        return [
            {
                "vendor_id": adapter.vendor_id,
                "supported_platforms": adapter.supported_platforms,
            }
            for adapter in self._adapters.values()
        ]
```

---

## 4. Extended Recipe Schema

### 4.1 Purpose

Recipes must encode platform-specific deployment contracts, not just quantization parameters.

### 4.2 Schema

```python
@dataclass
class RecipeSpec:
    """Complete quantization recipe specification."""
    
    recipe_id: str
    version: int
    project_id: str
    user_id: str
    status: str  # draft | validated | approved | executing | passed | failed
    
    # Source
    source: RecipeSource
    
    # Model
    model: ModelSpec
    
    # Quantization
    quantization: QuantizationSpec
    
    # Calibration
    calibration: CalibrationSpec
    
    # Evaluation
    evaluation: EvaluationSpec
    
    # Execution
    execution: ExecutionSpec
    
    # Platform Target (NEW)
    platform: PlatformSpec
    
    # Device Farm
    device_farm: DeviceFarmSpec
    
    # Acceptance
    acceptance: AcceptanceSpec
    
    # Rollback
    rollback: RollbackSpec
    
    # Vendor Extensions (NEW)
    vendor_extensions: dict[str, Any]
    
    # Metadata
    created_at: str
    updated_at: str
    approval: ApprovalSpec | None
    validation: ValidationSpec | None


@dataclass
class PlatformSpec:
    """Platform-specific deployment configuration."""
    
    # Target Platform
    platform_id: str                    # "mediatek-dimensity-9400"
    vendor: str                         # "mediatek"
    os: str                             # "android-14"
    
    # Inference Path
    inference_path: str                 # "online" | "offline"
    
    # Runtime
    runtime: str                        # "neuron-runtime" | "tflite" | "qnn"
    runtime_version: str | None
    
    # Converter/Compiler
    converter: str | None               # "np-converter"
    converter_version: str | None
    compiler: str | None                # "ncc-tflite"
    compiler_version: str | None
    
    # Hardware Constraints
    max_model_size_gb: float
    max_context_length: int
    supported_ops: list[str] | None     # None = use platform profile
    
    # CPU Fallback
    cpu_fallback_allowed: bool
    cpu_fallback_ops: list[str] | None  # Specific ops that can fallback
    
    # Packaging
    output_format: str                  # "dla" | "qnn-context" | "coreml" | "tflite"
    packaging_config: dict[str, Any]


@dataclass
class VendorExtensions:
    """Vendor-specific recipe extensions."""
    
    # NVIDIA
    nvidia: NVIDIAExtension | None
    
    # MediaTek
    mediatek: MediaTekExtension | None
    
    # Qualcomm
    qualcomm: QualcommExtension | None
    
    # Apple
    apple: AppleExtension | None


@dataclass
class MediaTekExtension:
    """MediaTek-specific recipe fields."""
    
    np_version: str                     # "NP8"
    mdla_version: str                   # "5.3"
    neuron_sdk_version: str
    converter_flags: dict[str, Any]
    compiler_flags: dict[str, Any]
    profiler: str                       # "neuron-studio"
```

### 4.3 MCP Tools for Extended Recipes

```python
@mcp.tool()
def start_platform_intake(
    project_id: str,
    user_id: str,
    utterance: str,
    target_platform: str | None = None,
) -> dict[str, Any]:
    """Start intake with platform-specific questions."""

@mcp.tool()
def validate_recipe_platform_compatibility(
    recipe_id: str,
) -> dict[str, Any]:
    """Validate recipe against platform constraints."""

@mcp.tool()
def get_platform_specific_questions(
    platform_id: str,
    current_answers: dict[str, Any],
) -> list[dict[str, Any]]:
    """Get platform-specific clarification questions."""
```

---

## 5. Stage-Aware Failure Analysis

### 5.1 Failure Phases

```
Source Model
    │
    ▼ [Phase: Conversion]
    │ - np-converter limitations
    │ - op compatibility issues
    │ - format conversion errors
    │
Converted Model (TFLite)
    │
    ▼ [Phase: Quantization]
    │ - calibration failures
    │ - accuracy regression
    │ - quantization errors
    │
Quantized Model
    │
    ▼ [Phase: Compilation]
    │ - ncc-tflite errors
    │ - hardware constraints
    │ - memory budget exceeded
    │
Compiled Artifact (.dla)
    │
    ▼ [Phase: Deployment]
    │ - transfer failures
    │ - device compatibility
    │ - installation errors
    │
Device Artifact
    │
    ▼ [Phase: Runtime]
    │ - neuron-runtime errors
    │ - CPU fallback triggers
    │ - execution failures
    │
Runtime Result
    │
    ▼ [Phase: KPI]
    │ - accuracy regression
    │ - latency regression
    │ - memory regression
    │ - power/thermal issues
    │
KPI Report
```

### 5.2 Failure Analysis Schema

```python
@dataclass
class FailureAnalysis:
    """Structured failure analysis result."""
    
    analysis_id: str
    failure_phase: str                  # "conversion" | "quantization" | "compile" | "deploy" | "runtime" | "kpi"
    root_cause_type: str                # "unsupported_op" | "hardware_constraint" | "accuracy_regression" | ...
    
    # Affected Components
    affected_ops: list[str]
    affected_devices: list[str]
    affected_artifacts: list[str]
    
    # Root Cause
    root_cause_description: str
    root_cause_evidence: dict[str, Any]
    
    # Remediation
    recommended_strategy: str           # "replace_ops" | "enable_cpu_fallback" | "mixed_precision" | ...
    recommended_recipe_changes: dict[str, Any]
    
    # Confidence
    confidence: float                   # 0.0 - 1.0
    requires_human_review: bool
    
    # Metadata
    created_at: str
    source_report_id: str
```

### 5.3 MCP Tools for Failure Analysis

```python
@mcp.tool()
def analyze_conversion_failure(
    artifact_id: str,
    error_logs: str | None = None,
) -> dict[str, Any]:
    """Analyze model conversion failure."""

@mcp.tool()
def analyze_compile_failure(
    artifact_id: str,
    error_logs: str | None = None,
) -> dict[str, Any]:
    """Analyze model compilation failure."""

@mcp.tool()
def analyze_runtime_failure(
    device_test_run_id: str,
    device_id: str | None = None,
) -> dict[str, Any]:
    """Analyze device runtime failure (CPU fallback, crash, etc.)."""

@mcp.tool()
def analyze_kpi_regression_detailed(
    kpi_report_id: str,
) -> dict[str, Any]:
    """Detailed KPI regression analysis with root cause classification."""
```

---

## 6. Profiling-First Observability

### 6.1 Profiling Integration

```python
@dataclass
class ProfileArtifact:
    """Profiling data linked to an artifact."""
    
    profile_id: str
    artifact_id: str
    device_id: str
    platform_id: str
    
    # Profiler
    profiler: str                       # "nsys" | "neuron-studio" | "xcode-instruments"
    profile_format: str                 # "nsys-rep" | "chrome-trace" | "perfetto"
    
    # Storage
    trace_uri: str                      # URI to trace file
    trace_size_mb: float
    
    # Extracted Metrics
    gpu_utilization_avg: float | None
    gpu_utilization_p95: float | None
    npu_loading_percent: float | None
    memory_bandwidth_gb_s: float | None
    
    # Bottlenecks
    identified_bottlenecks: list[ProfileBottleneck]
    
    # Recommendations
    optimization_recommendations: list[str]
    
    # Metadata
    created_at: str
    duration_seconds: float


@dataclass
class ProfileBottleneck:
    """Identified performance bottleneck."""
    
    bottleneck_type: str                # "memory_bandwidth" | "compute_bound" | "kernel_launch_overhead"
    severity: str                       # "critical" | "warning" | "info"
    location: str                       # Kernel name or operation
    impact_percent: float               # Estimated impact on total latency
    recommendation: str
```

### 6.2 MCP Tools for Profiling

```python
@mcp.tool()
def collect_device_profile(
    artifact_id: str,
    device_id: str,
    profiler: str = "auto",
    profile_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect profiling data from a device."""

@mcp.tool()
def analyze_profile(
    profile_id: str,
) -> dict[str, Any]:
    """Analyze profiling data and identify bottlenecks."""

@mcp.tool()
def get_profile_recommendations(
    profile_id: str,
) -> dict[str, Any]:
    """Get optimization recommendations from profile analysis."""
```

---

## 7. Enhanced KPI Report Schema

### 7.1 Extended KPI Fields

```python
@dataclass
class DeviceKPIReport:
    """Comprehensive device KPI report."""
    
    kpi_report_id: str
    device_test_run_id: str
    artifact_id: str
    recipe_id: str
    project_id: str
    
    # Device Info
    device_id: str
    platform_id: str
    vendor: str
    soc: str
    os_version: str
    
    # Model Info
    model_name: str
    quantization_method: str
    output_format: str                  # "dla" | "qnn-context" | "tflite"
    
    # Accuracy
    accuracy_drop: float
    baseline_accuracy: float
    quantized_accuracy: float
    
    # Latency
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float | None
    
    # LLM-Specific
    first_token_latency_ms: float | None
    tokens_per_second: float | None
    
    # Memory
    memory_peak_mb: int
    memory_budget_mb: int
    
    # Power/Thermal
    power_mw: int | None
    thermal_c: float | None
    
    # NPU/Accelerator
    npu_loading_percent: float | None
    npu_frequency_mhz: float | None
    
    # Fallback
    cpu_fallback_count: int
    cpu_fallback_ops: list[str]
    
    # Unsupported Ops
    unsupported_op_count: int
    unsupported_ops: list[str]
    
    # Profiling
    profile_id: str | None
    profile_trace_uri: str | None
    
    # Verdict
    passed: bool
    failed_kpis: list[str]
    
    # Acceptance
    acceptance_criteria: dict[str, Any]
    
    # Metadata
    created_at: str
    sdk_version: str | None
    converter_version: str | None
    compiler_version: str | None
```

---

## 8. Enhanced Device Farm

### 8.1 Device Schema

```python
@dataclass
class Device:
    """Device farm device specification."""
    
    device_id: str
    device_pool_id: str
    
    # Hardware
    vendor: str                         # "samsung" | "xiaomi" | "oneplus"
    model: str                          # "Galaxy S24 Ultra"
    platform: str                       # "android" | "ios"
    soc: str                            # "snapdragon-8gen3"
    
    # Accelerators
    accelerators: list[AcceleratorSpec]
    
    # Software
    os_version: str                     # "android-14"
    sdk_version: str | None
    
    # Capabilities
    supported_runtimes: list[str]       # ["neuron-runtime", "tflite", "qnn"]
    inference_paths: list[str]          # ["online", "offline"]
    
    # Status
    status: str                         # "ready" | "busy" | "offline" | "maintenance"
    last_heartbeat_at: str | None
    
    # Connectivity
    connection_type: str                # "usb" | "wifi" | "cloud"
    adb_device_id: str | None
    
    # Capabilities Matrix
    max_model_size_gb: float
    max_context_length: int
    supported_ops: list[str] | None     # None = use platform profile
```

### 8.2 Device Matrix Generation

```python
@mcp.tool()
def create_platform_aware_device_matrix(
    device_pool_id: str,
    platform_id: str | None = None,
    vendor: str | None = None,
    soc: str | None = None,
    min_os_version: str | None = None,
    max_devices: int = 8,
    coverage_strategy: str = "representative",
) -> dict[str, Any]:
    """Create device matrix with platform-aware selection."""

@mcp.tool()
def get_platform_coverage_report(
    device_pool_id: str,
    platform_ids: list[str],
) -> dict[str, Any]:
    """Report device coverage for target platforms."""
```

---

## 9. Production State Management

### 9.1 Migration Path

```python
# Current: JsonStateStore
# Target: Pluggable backend

class StateStore(ABC):
    """Abstract state store interface."""
    
    @abstractmethod
    def list(self, collection: str) -> list[dict[str, Any]]: ...
    
    @abstractmethod
    def get(self, collection: str, item_id: str) -> dict[str, Any] | None: ...
    
    @abstractmethod
    def upsert(self, collection: str, item_id: str, item: dict[str, Any]) -> dict[str, Any]: ...
    
    @abstractmethod
    def patch(self, collection: str, item_id: str, patch: dict[str, Any]) -> dict[str, Any]: ...
    
    @abstractmethod
    def delete(self, collection: str, item_id: str) -> bool: ...


class JsonStateStore(StateStore):
    """JSON file-based store (current, for development)."""
    ...


class PostgresStateStore(StateStore):
    """PostgreSQL-backed store (production)."""
    ...


class RedisStateStore(StateStore):
    """Redis-backed store (caching layer)."""
    ...
```

### 9.2 Configuration

```python
@dataclass
class Settings:
    """Enhanced settings with production backends."""
    
    # State Backend
    state_backend: str                  # "json" | "postgres" | "redis"
    postgres_dsn: str | None
    redis_url: str | None
    
    # Object Storage
    artifact_backend: str               # "local" | "s3" | "gcs"
    s3_bucket: str | None
    s3_prefix: str | None
    
    # Message Queue
    event_backend: str                  # "memory" | "redis" | "kafka"
    kafka_brokers: str | None
    
    # Auth
    auth_backend: str                   # "none" | "oidc" | "api-key"
    oidc_issuer_url: str | None
    oidc_client_id: str | None
```

---

## 10. Security and Multi-Tenancy

### 10.1 Auth Model

```python
@dataclass
class AuthContext:
    """Request authentication context."""
    
    user_id: str
    project_id: str
    roles: list[str]                    # ["admin", "engineer", "viewer"]
    permissions: list[str]              # ["recipe:create", "gpu:lease", ...]
    quota: QuotaSpec
    
    # Audit
    request_id: str
    timestamp: str


@dataclass
class QuotaSpec:
    """Project-level resource quotas."""
    
    max_gpu_hours_per_day: float
    max_concurrent_leases: int
    max_artifacts_per_project: int
    max_device_tests_per_day: int
```

### 10.2 RBAC Permissions

| Permission | Description |
|------------|-------------|
| `recipe:create` | Create new recipes |
| `recipe:validate` | Validate recipes |
| `recipe:approve` | Approve recipes for execution |
| `gpu:lease` | Request GPU leases |
| `gpu:release` | Release GPU leases |
| `device:test` | Submit device farm tests |
| `artifact:promote` | Promote artifacts |
| `admin:manage` | Manage users and quotas |

---

## 11. New MCP Tools Summary

### 11.1 Platform Registry Tools

| Tool | Purpose |
|------|---------|
| `list_platform_profiles` | List available platform profiles |
| `get_platform_profile` | Get detailed platform profile |
| `check_op_compatibility` | Check op support on platform |
| `get_platform_quantization_options` | Get quantization schemes |

### 11.2 Vendor Adapter Tools

| Tool | Purpose |
|------|---------|
| `list_vendor_adapters` | List registered adapters |
| `get_vendor_adapter` | Get adapter for vendor |
| `convert_model_vendor` | Convert model using vendor adapter |
| `compile_model_vendor` | Compile model using vendor adapter |
| `deploy_to_device` | Deploy artifact to device |
| `run_device_inference` | Run inference on device |
| `collect_device_profile` | Collect profiling data |

### 11.3 Enhanced Failure Analysis Tools

| Tool | Purpose |
|------|---------|
| `analyze_conversion_failure` | Analyze conversion failures |
| `analyze_compile_failure` | Analyze compilation failures |
| `analyze_runtime_failure` | Analyze runtime failures |
| `analyze_kpi_regression_detailed` | Detailed KPI regression analysis |

### 11.4 Enhanced Device Farm Tools

| Tool | Purpose |
|------|---------|
| `create_platform_aware_device_matrix` | Platform-aware device selection |
| `get_platform_coverage_report` | Device coverage report |
| `get_device_profile` | Get device profiling data |
| `analyze_device_profile` | Analyze profiling data |

---

## 12. Implementation Roadmap

### Phase 1: Platform Foundation (Weeks 1-4)
- [ ] Implement `PlatformProfile` schema and registry
- [ ] Add `PlatformSpec` to recipe schema
- [ ] Create `list_platform_profiles`, `get_platform_profile` tools
- [ ] Add platform-specific intake questions

### Phase 2: Vendor Adapters (Weeks 5-8)
- [ ] Implement `VendorAdapter` abstract interface
- [ ] Create `NVIDIATensorRTAdapter` (reference implementation)
- [ ] Create `MediaTekNeuroPilotAdapter`
- [ ] Add adapter registry and routing

### Phase 3: Stage-Aware Failure (Weeks 9-10)
- [ ] Implement `FailureAnalysis` schema
- [ ] Add `analyze_conversion_failure` tool
- [ ] Add `analyze_compile_failure` tool
- [ ] Add `analyze_runtime_failure` tool

### Phase 4: Profiling Integration (Weeks 11-12)
- [ ] Implement `ProfileArtifact` schema
- [ ] Add `collect_device_profile` tool
- [ ] Add `analyze_profile` tool
- [ ] Link profiles to KPI reports

### Phase 5: Production Hardening (Weeks 13-16)
- [ ] Implement `StateStore` interface
- [ ] Add `PostgresStateStore`
- [ ] Add auth context and RBAC
- [ ] Add quota enforcement

---

## 13. Appendix: MediaTek NeuroPilot Integration Details

### 13.1 Conversion Pipeline

```
Source Model (PyTorch/ONNX)
    │
    ▼ np-converter
    │ - Check op compatibility
    │ - Convert to TFLite
    │ - Report unsupported ops
    │
Converted TFLite
    │
    ▼ Post-Training Quantization
    │ - Load calibration data
    │ - Apply INT8 quantization
    │ - Validate accuracy
    │
Quantized TFLite
    │
    ▼ ncc-tflite (Neuron Compiler)
    │ - Compile to DLA format
    │ - Set NPU targets
    │ - Generate binary
    │
Compiled .dla
    │
    ▼ Deployment
    │ - Push to device via ADB
    │ - Load into Neuron Runtime
    │ - Run inference
    │
Device Result
```

### 13.2 Supported Operations (MediaTek NP8)

**Compute Operations:**
- Conv2D, DepthwiseConv2D, ConvTranspose2D
- MatMul, BatchMatMul
- FullyConnected

**Activation Operations:**
- ReLU, ReLU6, LeakyReLU, PReLU
- Sigmoid, Tanh, Swish, GELU, SiLU
- Softmax, LogSoftmax

**Normalization Operations:**
- BatchNorm, LayerNorm, RMSNorm
- InstanceNorm, GroupNorm

**Pooling Operations:**
- MaxPool, AveragePool, GlobalAveragePool

**Element-wise Operations:**
- Add, Sub, Mul, Div, Pow
- Abs, Neg, Exp, Log, Sqrt

**Reduction Operations:**
- ReduceSum, ReduceMean, ReduceMax, ReduceMin

**Tensor Operations:**
- Reshape, Transpose, Concat, Split
- Gather, Scatter, Slice, Pad

### 13.3 Quantization Schemes

| Scheme | Bits | Calibration | Use Case |
|--------|------|-------------|----------|
| INT8 | 8 | PTQ | Default, good accuracy/speed tradeoff |
| INT4 | 4 | PTQ + AWQ/GPTQ | Maximum compression, may lose accuracy |
| Mixed | 4/8 | Sensitivity analysis | Sensitive layers stay INT8 |
| FP16 | 16 | None | Maximum accuracy, larger model |

---

## 14. Appendix: Qualcomm QNN Integration Details

### 14.1 Conversion Pipeline

```
Source Model (PyTorch/ONNX)
    │
    ▼ qnn-converter
    │ - Convert to QNN IR
    │ - Check HTP compatibility
    │
QNN Model
    │
    ▼ Quantization
    │ - Apply INT8/INT16 quantization
    │ - Calibrate with representative data
    │
Quantized QNN Model
    │
    ▼ qnn-context-binary-generator
    │ - Generate context binary for HTP
    │ - Optimize for target SoC
    │
QNN Context Binary
    │
    ▼ Deployment
    │ - Push to device
    │ - Load into QNN runtime
    │
Device Result
```

---

## 15. Appendix: Apple CoreML Integration Details

### 15.1 Conversion Pipeline

```
Source Model (PyTorch)
    │
    ▼ coremltools
    │ - Trace model
    │ - Convert to CoreML format
    │ - Apply optimizations
    │
CoreML Model (.mlpackage)
    │
    ▼ Quantization
    │ - Apply INT8 quantization (palettization)
    │ - Or FP16 (default)
    │
Quantized CoreML Model
    │
    ▼ Compilation
    │ - Set compute units (ANE/GPU/CPU)
    │ - Compile for target device
    │
Compiled CoreML Model
    │
    ▼ Deployment
    │ - Bundle with app
    │ - Load on device
    │
Device Result
```

---

*End of Design Document*
