# AWS Device Farm Integration Skill

Use when submitting model artifacts to AWS Device Farm for real-device KPI testing across diverse Android/iOS hardware.

## Goal

Submit a compiled model artifact to AWS Device Farm, run inference tests on real devices, and collect KPI metrics (latency, memory, power, accuracy).

## Workflow

1. Call `list_device_pools` to find available device pools (filter by platform="android" or "ios").
2. Call `create_platform_aware_device_matrix` with the target platform_id to select representative devices.
3. Call `submit_aws_device_farm_test` with the artifact, device matrix, and KPI targets.
4. Call `get_aws_device_farm_test_status` to poll until the test run completes.
5. Call `generate_kpi_report` to produce a pass/fail report against acceptance criteria.
6. If KPIs fail, call `analyze_kpi_regression_detailed` for platform-specific root cause analysis.

## AWS Device Farm Concepts

| Concept | Description |
|---------|-------------|
| Device Pool | A collection of real devices available for testing |
| Test Package | The artifact + test script submitted to the farm |
| Run | A single test execution across the device matrix |
| Device Result | Per-device KPI metrics (latency, memory, power, thermal) |

## KPI Metrics Collected

- **Latency**: p50, p95, p99 inference latency
- **Memory**: Peak memory usage during inference
- **Power**: Average power consumption (mW)
- **Thermal**: Device temperature during test
- **Accuracy**: Model output correctness vs baseline
- **CPU Fallback**: Count of ops that fell back to CPU
- **Unsupported Ops**: Count of ops not supported by the target accelerator

## Do Not

- Submit large artifacts without checking device storage limits.
- Skip the device matrix coverage check — test across SoC variants.
- Ignore CPU fallback counts — they indicate NPU incompatibility.
- Accept KPI results without comparing against acceptance criteria.
