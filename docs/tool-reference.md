# Tool Reference

This reference groups the MCP tools by operational area. Tools return JSON-native dictionaries with `status`, `summary`, `data`, and often `next_actions`.

## System and Catalog

| Tool | Purpose |
| --- | --- |
| `health_check` | Check server state paths and catalog readiness. |
| `list_runtime_envs` | List approved Docker/conda/runtime environments. |
| `list_toolchains` | List registered task templates. |
| `validate_runtime_env` | Validate an approved runtime environment. |
| `list_agent_skills` | List local/hybrid skills available to the agent. |
| `get_agent_skill` | Read one skill contract. |
| `generate_hybrid_workflow_plan` | Generate a plan whose steps can be skills, tools, approvals, or external systems. |

## Intake and Recipe Lifecycle

| Tool | Purpose |
| --- | --- |
| `start_quantization_intake` | Start from a short natural-language request and return missing questions. |
| `answer_intake_questions` | Record clarification answers. |
| `synthesize_quantization_recipe` | Create an auditable recipe spec from intake. |
| `validate_quantization_recipe` | Validate recipe blockers and warnings. |
| `approve_quantization_recipe` | Approve a validated recipe for execution. |
| `list_quantization_recipes` | List recipe specs by project or status. |
| `create_recipe_revision_from_feedback` | Create a new recipe revision after KPI failures. |

## Compute Control Plane

| Tool | Purpose |
| --- | --- |
| `list_compute_pools` | List GPU compute pools. |
| `list_compute_nodes` | List GPU worker nodes. |
| `register_compute_node` | Register a worker node under a pool. |
| `heartbeat_compute_node` | Update worker heartbeat and metrics. |
| `get_compute_capacity` | Summarize pool/node capacity. |
| `select_compute_pool` | Select a compute pool for a recipe or requirement. |
| `create_execution_plan_from_recipe` | Create a control-plane execution plan from a recipe. |

## Resource Governance

| Tool | Purpose |
| --- | --- |
| `get_resource_snapshot` | Inspect GPUs, active leases, jobs, queue, and disk. |
| `estimate_resource_need` | Estimate GPU/CPU/RAM/disk for a model stage. |
| `request_resource_lease` | Request a GPU lease before running GPU jobs. |
| `renew_resource_lease` | Extend an active lease TTL. |
| `release_resource_lease` | Release a lease after work is done. |
| `get_queue_status` | Inspect queued lease requests. |
| `get_user_usage` | Summarize user/project lease and job usage. |
| `list_gpu_processes` | List GPU processes known to the server. |
| `cleanup_orphan_jobs` | Detect orphan jobs without killing unrelated processes. |

## Workspace and Files

| Tool | Purpose |
| --- | --- |
| `create_workspace` | Create an isolated run workspace. |
| `list_workspace_files` | List files under a workspace root. |
| `read_text_file` | Read small text files in a workspace. |
| `write_config_file` | Write JSON/YAML/TOML/text config files in a workspace. |
| `stage_model` | Stage or reference a model in the workspace. |
| `stage_dataset` | Stage a known dataset in the workspace. |
| `compute_checksum` | Compute checksums for workspace files or directories. |
| `get_disk_usage` | Get workspace disk usage versus quota. |
| `cleanup_workspace` | Clean outputs or the entire workspace. |

## Model Intake

| Tool | Purpose |
| --- | --- |
| `register_model` | Register model URI, framework, task type, and size. |
| `inspect_model` | Submit model architecture/config/tokenizer inspection. |
| `validate_model_load` | Load the model in a GPU runtime and capture peak memory. |
| `validate_tokenizer` | Validate tokenizer metadata. |
| `validate_chat_template` | Validate chat template availability. |
| `check_backend_compatibility` | Check model/backend/hardware compatibility. |

## Data and Baseline

| Tool | Purpose |
| --- | --- |
| `list_datasets` | List known calibration and evaluation datasets. |
| `prepare_calibration_dataset` | Prepare calibration metadata and optional staging. |
| `validate_eval_dataset` | Validate eval dataset compatibility. |
| `run_baseline_eval` | Run baseline accuracy metrics. |
| `run_baseline_benchmark` | Run baseline performance benchmark. |

## Quantization

| Tool | Purpose |
| --- | --- |
| `recommend_quant_recipes` | Recommend recipes based on model, hardware, and constraints. |
| `create_quant_recipe` | Create a derived recipe with overrides. |
| `run_quantization` | Run an approved quantization template. |
| `validate_quantized_model` | Validate quantized artifact load. |
| `run_quantized_eval` | Evaluate quantized candidate versus baseline. |

## Benchmark, Profile, Compile, Export

| Tool | Purpose |
| --- | --- |
| `run_benchmark` | Benchmark latency, throughput, memory, and utilization. |
| `compare_benchmarks` | Rank candidate benchmark results. |
| `run_profiler` | Collect profiler results and bottleneck hints. |
| `compile_model` | Compile model artifact for an approved backend. |
| `export_model` | Register an exported serving artifact. |
| `package_serving_bundle` | Convenience wrapper for serving bundle export. |
| `allocate_service_port` | Allocate a managed port for temporary serving. |
| `release_service_port` | Release a managed service port. |
| `start_inference_service` | Start a managed temporary inference service. |
| `get_service_health` | Check managed inference service readiness. |
| `stop_inference_service` | Stop a managed inference service and release its port. |

## Device Farm and KPI Feedback

| Tool | Purpose |
| --- | --- |
| `list_device_pools` | List device-farm pools. |
| `list_devices` | List devices by pool, platform, SoC, or status. |
| `create_device_test_matrix` | Build a test matrix from device filters. |
| `submit_device_farm_test` | Submit an artifact to device-farm KPI testing. |
| `get_device_test_status` | Read device test status and raw KPI results. |
| `generate_kpi_report` | Convert raw device results into pass/fail KPI report. |
| `analyze_kpi_regression` | Analyze failed KPIs and propose recipe feedback strategy. |
| `create_recipe_feedback` | Persist structured feedback for recipe revision. |

## Jobs and Guided Runs

| Tool | Purpose |
| --- | --- |
| `submit_job` | Submit a registered task template directly. |
| `get_job_status` | Inspect job status, result, failure, and artifacts. |
| `get_job_logs` | Read job logs. |
| `get_job_metrics` | Read job metrics time series. |
| `cancel_job` | Cancel an active job. |
| `retry_job` | Retry a job with optional overrides. |
| `analyze_job_failure` | Analyze a failed job and suggest next actions. |
| `start_model_onboarding` | Create a guided onboarding run. |
| `run_onboarding_stage` | Run one stage of the guided onboarding workflow. |
| `get_next_recommended_action` | Ask the server for the next safe action. |
| `summarize_onboarding_status` | Summarize run, jobs, artifacts, and next action. |
| `generate_onboarding_report` | Generate a reproducible Markdown report. |
| `get_artifact` | Read artifact metadata and lineage. |
| `promote_artifact` | Promote candidate to staging or production with approval checks. |

## Recommended Agent Behavior

Agents should prefer the guided workflow:

```text
start_quantization_intake
answer_intake_questions
synthesize_quantization_recipe
validate_quantization_recipe
generate_hybrid_workflow_plan
approve_quantization_recipe
select_compute_pool
create_execution_plan_from_recipe
request_resource_lease
run_quantization
submit_device_farm_test
generate_kpi_report
analyze_kpi_regression
```

Agents should use local skills for reasoning-heavy steps and MCP tools for shared state, remote execution, and auditability.
