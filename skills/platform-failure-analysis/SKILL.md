# Platform-Aware Failure Analysis Skill

Use when conversion, compilation, runtime, or KPI failures occur during platform-specific model deployment.

## Goal

Analyze failures across the full pipeline (conversion → quantization → compile → deploy → runtime → KPI) with vendor-specific remediation strategies.

## Failure Phases

| Phase | Common Failures | Analysis Tool |
|-------|----------------|---------------|
| **Conversion** | Unsupported ops, format errors, shape mismatches | `analyze_conversion_failure` |
| **Quantization** | Calibration failure, accuracy regression | `analyze_kpi_regression_detailed` |
| **Compilation** | Hardware constraints, memory budget exceeded | `analyze_compile_failure` |
| **Deployment** | Transfer failure, device compatibility | `analyze_runtime_failure` |
| **Runtime** | CPU fallback, execution crash, timeout | `analyze_runtime_failure` |
| **KPI** | Accuracy/latency/memory regression | `analyze_kpi_regression_detailed` |

## Workflow

1. Identify the failure phase from the error context.
2. Call the appropriate analysis tool for that phase.
3. Review the root cause and recommended remediation strategy.
4. If remediation requires recipe changes, call `create_recipe_feedback`.
5. Call `create_recipe_revision_from_feedback` to generate a revised recipe.
6. Ask the engineer before approving the revised recipe.

## Vendor-Specific Remediation

### MediaTek NeuroPilot
- **Unsupported op**: Replace with supported equivalent or enable CPU fallback
- **Compile failure**: Check NP/MDLA version compatibility, reduce model size
- **CPU fallback**: Identify which ops fell back, replace or exclude them

### Qualcomm QNN
- **Unsupported op**: Check HTP version support, use QNN compatibility checker
- **Compile failure**: Verify SoC target, check context binary size limits
- **CPU fallback**: Switch to mixed precision or replace unsupported ops

## Do Not

- Skip phase-specific analysis — generic "something failed" is not actionable.
- Apply the same fix to all vendors — each has different constraints.
- Ignore CPU fallback warnings — they degrade performance significantly.
- Create recipe revisions without engineer approval.
