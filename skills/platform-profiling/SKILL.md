# Device Profiling Skill

Use when collecting and analyzing performance profiling data from target devices (Neuron Studio, Qualcomm Profiler, ADB).

## Goal

Profile model inference on device to identify performance bottlenecks (NPU utilization, memory bandwidth, kernel occupancy, CPU fallback) and generate optimization recommendations.

## Workflow

1. Call `collect_device_profile` with the artifact_id, device_id, and profiler type.
2. Call `analyze_profile` to extract bottleneck metrics and root causes.
3. Call `get_profile_recommendations` to get actionable optimization suggestions.
4. If bottlenecks indicate recipe issues, create recipe feedback.

## Profiling Tools by Vendor

| Vendor | Tool | Key Metrics |
|--------|------|-------------|
| MediaTek | Neuron Studio | NPU frequency, NPU loading, DRAM utilization, workflow traces |
| Qualcomm | Qualcomm Profiling Tools | HTP utilization, memory bandwidth, kernel execution time |
| Generic | ADB / systrace | CPU usage, memory, power, thermal |

## Key Metrics

- **NPU Loading %**: How busy the NPU is (target: >80%)
- **Memory Bandwidth**: Data transfer bottleneck (target: <70% of peak)
- **CPU Fallback Count**: Ops not running on NPU (target: 0)
- **Kernel Occupancy**: GPU/NPU thread utilization (target: >60%)
- **Power Consumption**: Average power during inference (compare against budget)

## Optimization Recommendations

| Bottleneck | Recommendation |
|------------|----------------|
| Low NPU loading | Increase batch size or concurrency |
| High memory bandwidth | Reduce model size or use mixed precision |
| CPU fallback | Replace unsupported ops or enable op replacement |
| Low kernel occupancy | Adjust tiling or padding configuration |
| High power | Reduce NPU frequency or use smaller model variant |

## Do Not

- Profile without a baseline — always compare against reference metrics.
- Ignore CPU fallback in profiling results — it hides performance issues.
- Skip thermal monitoring — throttling degrades sustained performance.
- Use profiling results as final acceptance criteria — they are diagnostic, not gatekeeping.
