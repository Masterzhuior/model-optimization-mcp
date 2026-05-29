# Qualcomm QNN Conversion Skill

Use when converting or compiling models for Qualcomm Hexagon NPU deployment (Snapdragon platforms).

## Goal

Convert a PyTorch/ONNX model to a QNN context binary using the Qualcomm AI Engine Direct SDK:
qnn-converter → QNN Model → qnn-context-binary-generator → context binary.

## Supported Platforms

- Snapdragon 8 Gen 3 (Hexagon NPU v75, 73 TOPS)
- Snapdragon 8 Gen 2 (Hexagon NPU v73, 48 TOPS)

## Workflow

1. Call `get_platform_profile` to load the target platform's supported ops and SDK version.
2. Call `check_op_compatibility` to verify the model's ops are supported on the HTP backend.
3. Call `convert_model_vendor` with vendor="qualcomm" to run qnn-converter (PyTorch/ONNX → QNN IR).
4. If conversion has unsupported ops, call `analyze_conversion_failure`.
5. Call `compile_model_vendor` with vendor="qualcomm" to generate the QNN context binary for HTP.
6. If compilation fails, call `analyze_compile_failure` for hardware constraint details.

## Conversion Pipeline

```
Source Model (PyTorch/ONNX)
  → qnn-converter → QNN Model
  → qnn-context-binary-generator → QNN Context Binary
```

## Key Decision Points

| Decision | Options | Guidance |
|----------|---------|----------|
| Backend | HTP, GPU, CPU | HTP for NPU; GPU for fallback; CPU for debugging |
| Precision | INT8, INT16, FP16 | INT8 for best performance; INT16 for better accuracy; FP16 for compatibility |
| Mixed precision | Yes, No | Use for models with sensitive layers that lose accuracy under INT8 |

## Do Not

- Skip the QNN compatibility check — some ops require specific HTP versions.
- Use INT4 without careful calibration — it can cause significant accuracy loss.
- Forget to set the correct HTP version for the target SoC.
