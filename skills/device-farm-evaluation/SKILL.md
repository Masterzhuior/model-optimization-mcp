# Device Farm Evaluation Skill

Use when the deployment target is mobile, edge, or device-specific.

## Workflow

1. Call `list_device_pools`.
2. Call `create_device_test_matrix`.
3. Package local metadata if needed.
4. Call `submit_device_farm_test`.
5. Call `get_device_test_status`.
6. Call `generate_kpi_report`.

## KPI Examples

- accuracy delta,
- latency p50/p95,
- memory peak,
- power,
- thermal,
- crash rate,
- load time.

