# MediaTek NeuroPilot Conversion Skill

Use when converting, quantizing, or compiling models for MediaTek NPU deployment (Dimensity/Genio platforms).

## Goal

Convert a PyTorch/ONNX model to a device-ready DLA artifact using the MediaTek NeuroPilot toolchain:
np-converter → PTQ → ncc-tflite → .dla binary.

## Supported Platforms

- Dimensity 9400 (APU 790, NP8, MDLA 5.3)
- Dimensity 9300 (APU 780, NP7, MDLA 5.2)
- Genio 720 / 510

## Workflow

1. Call `get_platform_profile` to load the target platform's supported ops, quantization schemes, and SDK versions.
2. Call `check_op_compatibility` to verify the model's ops are supported on the target NPU.
3. Call `convert_model_vendor` with vendor="mediatek" to run np-converter (PyTorch/ONNX → TFLite).
4. If conversion has unsupported ops, call `analyze_conversion_failure` to identify workarounds.
5. Call `quantize_model_vendor` with vendor="mediatek" to run PTQ (INT8/INT4/mixed).
6. Call `compile_model_vendor` with vendor="mediatek" to compile TFLite → DLA using ncc-tflite.
7. If compilation fails, call `analyze_compile_failure` for hardware constraint details.

## Conversion Pipeline

```
Source Model (PyTorch/ONNX)
  → np-converter → TFLite
  → PTQ Calibration → Quantized TFLite
  → ncc-tflite → .dla binary
```

## Key Decision Points

| Decision | Options | Guidance |
|----------|---------|----------|
| Quantization scheme | INT8, INT4, Mixed | INT8 is safest; INT4 for maximum compression; Mixed for sensitive layers |
| Inference path | Online, Offline | Offline (DLA) is faster but less flexible; Online (TFLite) allows CPU fallback |
| CPU fallback | Allow, Disallow | Allow for first deployment; disallow for production if all ops are supported |

## Do Not

- Skip op compatibility check before conversion.
- Use FP16 directly on NPU (must be quantized first).
- Ignore unsupported ops warnings — they cause runtime CPU fallback.
- Compile to DLA without validating the quantized TFLite first.
