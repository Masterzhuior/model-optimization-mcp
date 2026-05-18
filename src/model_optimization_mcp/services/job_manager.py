"""Asynchronous job runner and whitelisted task-template execution."""

from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from typing import Any

from ..config import Settings
from ..schemas import JobStatus
from ..store import JsonStateStore
from ..utils import short_id, utc_now_iso
from .artifacts import ArtifactManager

ACTIVE_STATUSES = {
    JobStatus.CREATED.value,
    JobStatus.ADMITTED.value,
    JobStatus.QUEUED.value,
    JobStatus.RESOURCE_ALLOCATED.value,
    JobStatus.PREPARING_WORKSPACE.value,
    JobStatus.PULLING_IMAGE.value,
    JobStatus.RUNNING.value,
    JobStatus.COLLECTING_METRICS.value,
    JobStatus.UPLOADING_ARTIFACTS.value,
    JobStatus.WAITING_FOR_APPROVAL.value,
    JobStatus.WAITING_FOR_RESOURCE.value,
}


class JobManager:
    def __init__(
        self,
        store: JsonStateStore,
        settings: Settings,
        artifacts: ArtifactManager,
    ):
        self.store = store
        self.settings = settings
        self.artifacts = artifacts
        self._threads: dict[str, threading.Thread] = {}

    def submit_job(
        self,
        *,
        template_id: str,
        project_id: str,
        user_id: str,
        workspace_id: str | None = None,
        lease_id: str | None = None,
        env_id: str = "llm-opt-cu124-v3",
        args: dict[str, Any] | None = None,
        run_id: str | None = None,
        priority: str = "normal",
        start: bool = True,
    ) -> dict[str, Any]:
        template = self.store.get("task_templates", template_id)
        if not template:
            raise ValueError(f"unknown template_id: {template_id}")

        if template.get("requires_gpu"):
            lease = self.store.get("leases", lease_id or "")
            if not lease or lease.get("status") != "allocated":
                status = JobStatus.WAITING_FOR_RESOURCE.value
            else:
                status = JobStatus.CREATED.value
        else:
            lease = None
            status = JobStatus.CREATED.value

        args = args or {}
        job_id = short_id("job")
        job = {
            "job_id": job_id,
            "template_id": template_id,
            "project_id": project_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "lease_id": lease_id,
            "run_id": run_id,
            "env_id": env_id,
            "priority": priority,
            "args": args,
            "args_hash": _hash_args(args),
            "status": status,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "logs": [],
            "metrics": {},
            "artifacts": [],
            "gpu_uuids": (lease or {}).get("allocated_gpu_uuids", []),
        }
        self.store.upsert("jobs", job_id, job)
        self._append_log(job_id, f"job created with template {template_id}")

        if start and status == JobStatus.CREATED.value:
            self._start_background(job_id)
        return self.get_job(job_id)

    def _start_background(self, job_id: str) -> None:
        thread = threading.Thread(target=self._execute_job, args=(job_id,), daemon=True)
        self._threads[job_id] = thread
        thread.start()

    def _execute_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        template = self.store.get("task_templates", job["template_id"]) or {}
        stages = [
            JobStatus.ADMITTED,
            JobStatus.RESOURCE_ALLOCATED,
            JobStatus.PREPARING_WORKSPACE,
            JobStatus.PULLING_IMAGE,
            JobStatus.RUNNING,
            JobStatus.COLLECTING_METRICS,
            JobStatus.UPLOADING_ARTIFACTS,
        ]
        if not template.get("requires_gpu"):
            stages = [JobStatus.ADMITTED, JobStatus.PREPARING_WORKSPACE, JobStatus.RUNNING]

        try:
            for stage in stages:
                latest = self.get_job(job_id)
                if latest.get("status") == JobStatus.CANCELLED.value:
                    self._append_log(job_id, "job cancellation acknowledged")
                    return
                self._set_status(job_id, stage.value)
                self._append_log(job_id, f"entered stage: {stage.value}")
                self._record_metrics(job_id, stage.value)
                time.sleep(self._stage_delay(template))

            result = self._complete_result(self.get_job(job_id), template)
            self._append_log(job_id, "job succeeded")
            self.store.patch(
                "jobs",
                job_id,
                {
                    "status": JobStatus.SUCCEEDED.value,
                    "result": result,
                    "updated_at": utc_now_iso(),
                    "ended_at": utc_now_iso(),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive guard around adapters
            self._append_log(job_id, f"job failed: {exc}")
            self.store.patch(
                "jobs",
                job_id,
                {
                    "status": JobStatus.FAILED.value,
                    "failure": {
                        "failure_type": exc.__class__.__name__,
                        "message": str(exc),
                    },
                    "updated_at": utc_now_iso(),
                    "ended_at": utc_now_iso(),
                },
            )

    def _stage_delay(self, template: dict[str, Any]) -> float:
        duration = float(template.get("default_duration_seconds", 2))
        speed = max(0.1, self.settings.simulation_speed)
        return max(0.01, min(duration * 0.03 / speed, 0.25))

    def _complete_result(self, job: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
        args = job.get("args", {})
        template_id = job["template_id"]
        rng = _rng(job["job_id"], args)

        if template_id == "inspect_model_v1":
            return self._result_inspect_model(job, args, rng)
        if template_id == "validate_model_load_v1":
            return self._result_validate_load(job, args, rng)
        if template_id == "baseline_eval_v1":
            return self._result_baseline_eval(job, args, rng)
        if template_id == "baseline_benchmark_v1":
            return self._result_baseline_benchmark(job, args, rng)
        if template_id == "quantize_model_v1":
            return self._result_quantize(job, args, rng)
        if template_id == "quantized_eval_v1":
            return self._result_quantized_eval(job, args, rng)
        if template_id == "benchmark_v1":
            return self._result_benchmark(job, args, rng)
        if template_id == "profile_v1":
            return self._result_profile(job, args, rng)
        if template_id == "compile_model_v1":
            return self._result_compile(job, args, rng)
        if template_id == "report_v1":
            return {"message": "report generation completed"}
        return {"message": "template completed", "template_id": template_id}

    def _result_inspect_model(
        self, job: dict[str, Any], args: dict[str, Any], rng: random.Random
    ) -> dict[str, Any]:
        model_id = args.get("model_id")
        model = self.store.get("models", model_id) if model_id else None
        model_name = (model or {}).get("model_name") or args.get("model_uri", "unknown-model")
        arch = _guess_architecture(model_name)
        parameter_count_b = float((model or {}).get("parameter_count_b", 7.0))
        result = {
            "model_id": model_id,
            "architecture": arch,
            "parameter_count_b": parameter_count_b,
            "dtype": args.get("dtype", "bf16"),
            "format": "safetensors",
            "tokenizer_found": True,
            "custom_ops": [],
            "max_position_embeddings": 32768 if "qwen" in arch else 4096,
            "unsupported_layers": [],
            "estimated_vram_gb": {
                "bf16": round(parameter_count_b * 2.2, 1),
                "int8": round(parameter_count_b * 1.15, 1),
                "int4": round(parameter_count_b * 0.62, 1),
            },
            "risk_flags": ["chat_template_needs_validation"] if rng.random() > 0.4 else [],
        }
        if model_id:
            self.store.patch("models", model_id, {"inspection": result, "status": "inspected"})
        return result

    def _result_validate_load(
        self, job: dict[str, Any], args: dict[str, Any], rng: random.Random
    ) -> dict[str, Any]:
        peak = round(12 + rng.random() * 8, 2)
        return {
            "load_success": True,
            "load_time_sec": round(20 + rng.random() * 40, 1),
            "peak_memory_gb": peak,
            "warnings": [],
        }

    def _result_baseline_eval(
        self, job: dict[str, Any], args: dict[str, Any], rng: random.Random
    ) -> dict[str, Any]:
        metrics = {
            "accuracy": round(0.81 + rng.random() * 0.03, 4),
            "rouge_l": round(0.72 + rng.random() * 0.04, 4),
            "exact_match": round(0.58 + rng.random() * 0.05, 4),
        }
        artifact = self.artifacts.register_artifact(
            artifact_type="eval_result",
            name=f"{job['job_id']}-baseline-eval",
            project_id=job["project_id"],
            metadata={"metrics": metrics, "eval_config": args.get("eval_config", {})},
            lineage={"job_id": job["job_id"], "run_id": job.get("run_id"), "model_id": args.get("model_id")},
        )
        self._attach_artifact(job["job_id"], artifact["artifact_id"])
        return {"baseline_id": artifact["artifact_id"], "metrics": metrics, "pass": True}

    def _result_baseline_benchmark(
        self, job: dict[str, Any], args: dict[str, Any], rng: random.Random
    ) -> dict[str, Any]:
        summary = {
            "throughput_tokens_per_sec": round(7200 + rng.random() * 1200, 1),
            "latency_p50_ms": round(54 + rng.random() * 8, 1),
            "latency_p95_ms": round(112 + rng.random() * 18, 1),
            "latency_p99_ms": round(160 + rng.random() * 24, 1),
            "gpu_memory_peak_gb": round(42 + rng.random() * 8, 1),
            "gpu_util_avg": round(0.72 + rng.random() * 0.12, 3),
        }
        artifact = self.artifacts.register_artifact(
            artifact_type="benchmark_result",
            name=f"{job['job_id']}-baseline-benchmark",
            project_id=job["project_id"],
            metadata={"summary": summary, "benchmark_config": args.get("benchmark_config", {})},
            lineage={"job_id": job["job_id"], "run_id": job.get("run_id"), "model_id": args.get("model_id")},
        )
        self._attach_artifact(job["job_id"], artifact["artifact_id"])
        return {"benchmark_id": artifact["artifact_id"], "summary": summary, "pass": True}

    def _result_quantize(
        self, job: dict[str, Any], args: dict[str, Any], rng: random.Random
    ) -> dict[str, Any]:
        recipe_id = args.get("recipe_id", "recipe-awq-int4-g128")
        recipe = self.store.get("recipes", recipe_id) or {}
        method = recipe.get("method", "awq")
        metadata = {
            "method": method,
            "weight_bits": recipe.get("weight_bits", 4),
            "group_size": recipe.get("group_size"),
            "size_gb": round(4 + rng.random() * 2, 2),
            "recipe_id": recipe_id,
            "calibration_artifact_id": args.get("calibration_artifact_id"),
        }
        artifact = self.artifacts.register_artifact(
            artifact_type="quantized_model",
            name=args.get("artifact_name") or f"{method}-candidate-{job['job_id']}",
            project_id=job["project_id"],
            metadata=metadata,
            lineage={
                "job_id": job["job_id"],
                "run_id": job.get("run_id"),
                "model_id": args.get("model_id"),
                "recipe_id": recipe_id,
            },
        )
        self._attach_artifact(job["job_id"], artifact["artifact_id"])
        return {
            "quant_artifact_id": artifact["artifact_id"],
            "method": method,
            "status": "success",
            "artifact_uri": artifact["uri"],
            "size_gb": metadata["size_gb"],
            "metadata": metadata,
        }

    def _result_quantized_eval(
        self, job: dict[str, Any], args: dict[str, Any], rng: random.Random
    ) -> dict[str, Any]:
        accuracy_drop = round(0.002 + rng.random() * 0.011, 4)
        metrics = {
            "accuracy": round(0.825 - accuracy_drop, 4),
            "rouge_l": round(0.739 - accuracy_drop * 0.8, 4),
            "exact_match": round(0.603 - accuracy_drop * 1.1, 4),
        }
        max_drop = float(args.get("acceptance_criteria", {}).get("max_accuracy_drop", 0.01))
        artifact = self.artifacts.register_artifact(
            artifact_type="eval_result",
            name=f"{job['job_id']}-quantized-eval",
            project_id=job["project_id"],
            metadata={
                "metrics": metrics,
                "diff_vs_baseline": {"accuracy_drop": accuracy_drop},
                "pass": accuracy_drop <= max_drop,
            },
            lineage={
                "job_id": job["job_id"],
                "run_id": job.get("run_id"),
                "artifact_id": args.get("quant_artifact_id"),
                "baseline_id": args.get("baseline_id"),
            },
        )
        quant_artifact_id = args.get("quant_artifact_id")
        if quant_artifact_id:
            quant_artifact = self.store.get("artifacts", quant_artifact_id)
            if quant_artifact:
                quant_artifact.setdefault("metadata", {})["eval"] = {
                    "accuracy_drop": accuracy_drop,
                    "metrics": metrics,
                    "pass": accuracy_drop <= max_drop,
                }
                self.store.upsert("artifacts", quant_artifact_id, quant_artifact)
        self._attach_artifact(job["job_id"], artifact["artifact_id"])
        return {
            "eval_id": artifact["artifact_id"],
            "metrics": metrics,
            "diff_vs_baseline": {"accuracy_drop": accuracy_drop},
            "pass": accuracy_drop <= max_drop,
        }

    def _result_benchmark(
        self, job: dict[str, Any], args: dict[str, Any], rng: random.Random
    ) -> dict[str, Any]:
        speedup = round(1.65 + rng.random() * 1.1, 2)
        summary = {
            "throughput_tokens_per_sec": round(8200 * speedup, 1),
            "latency_p50_ms": round(54 / speedup, 1),
            "latency_p95_ms": round(112 / speedup, 1),
            "latency_p99_ms": round(160 / speedup, 1),
            "gpu_memory_peak_gb": round(22 + rng.random() * 7, 1),
            "gpu_util_avg": round(0.78 + rng.random() * 0.12, 3),
            "speedup": speedup,
        }
        artifact = self.artifacts.register_artifact(
            artifact_type="benchmark_result",
            name=f"{job['job_id']}-benchmark",
            project_id=job["project_id"],
            metadata={"summary": summary, "benchmark_config": args.get("benchmark_config", {})},
            lineage={"job_id": job["job_id"], "run_id": job.get("run_id"), "artifact_id": args.get("artifact_id")},
        )
        target_artifact_id = args.get("artifact_id")
        if target_artifact_id:
            target = self.store.get("artifacts", target_artifact_id)
            if target:
                target.setdefault("metadata", {})["benchmark"] = {
                    "speedup": speedup,
                    "summary": summary,
                    "pass": speedup >= float(args.get("min_speedup", 1.0)),
                }
                self.store.upsert("artifacts", target_artifact_id, target)
        self._attach_artifact(job["job_id"], artifact["artifact_id"])
        return {"benchmark_id": artifact["artifact_id"], "summary": summary, "pass": True}

    def _result_profile(
        self, job: dict[str, Any], args: dict[str, Any], rng: random.Random
    ) -> dict[str, Any]:
        bottlenecks = ["kv_cache_memory_bandwidth", "attention_kernel_occupancy"]
        artifact = self.artifacts.register_artifact(
            artifact_type="profile_result",
            name=f"{job['job_id']}-profile",
            project_id=job["project_id"],
            metadata={
                "profiler": args.get("profiler", "nsys"),
                "bottlenecks": bottlenecks,
                "gpu_idle_pct": round(rng.random() * 0.08, 3),
            },
            lineage={"job_id": job["job_id"], "run_id": job.get("run_id"), "artifact_id": args.get("artifact_id")},
        )
        self._attach_artifact(job["job_id"], artifact["artifact_id"])
        return {
            "profile_id": artifact["artifact_id"],
            "bottlenecks": bottlenecks,
            "suggested_actions": [
                "increase batch/concurrency until p95 latency approaches SLO",
                "check paged KV cache configuration",
            ],
        }

    def _result_compile(
        self, job: dict[str, Any], args: dict[str, Any], rng: random.Random
    ) -> dict[str, Any]:
        compiler = args.get("compiler", "tensorrt-llm")
        artifact = self.artifacts.register_artifact(
            artifact_type="compiled_model",
            name=f"{compiler}-compiled-{job['job_id']}",
            project_id=job["project_id"],
            metadata={
                "compiler": compiler,
                "target_format": args.get("target_format", compiler),
                "engine_size_gb": round(3.5 + rng.random(), 2),
            },
            lineage={"job_id": job["job_id"], "run_id": job.get("run_id"), "source_artifact_id": args.get("artifact_id")},
        )
        self._attach_artifact(job["job_id"], artifact["artifact_id"])
        return {
            "compiled_artifact_id": artifact["artifact_id"],
            "compiler": compiler,
            "artifact_uri": artifact["uri"],
        }

    def _set_status(self, job_id: str, status: str) -> None:
        self.store.patch("jobs", job_id, {"status": status, "updated_at": utc_now_iso()})

    def _append_log(self, job_id: str, message: str) -> None:
        job = self.store.get("jobs", job_id)
        if not job:
            return
        logs = job.get("logs", [])
        logs.append({"timestamp": utc_now_iso(), "message": message})
        self.store.patch("jobs", job_id, {"logs": logs, "updated_at": utc_now_iso()})

    def _record_metrics(self, job_id: str, stage: str) -> None:
        job = self.store.get("jobs", job_id)
        if not job:
            return
        metrics = job.get("metrics", {})
        samples = metrics.setdefault("samples", [])
        samples.append(
            {
                "timestamp": utc_now_iso(),
                "stage": stage,
                "gpu_utilization": 0.0 if stage != "running" else 0.77,
                "gpu_memory_gb": 0.0 if stage != "running" else 32.0,
            }
        )
        self.store.patch("jobs", job_id, {"metrics": metrics, "updated_at": utc_now_iso()})

    def _attach_artifact(self, job_id: str, artifact_id: str) -> None:
        job = self.store.get("jobs", job_id)
        if not job:
            return
        artifact_ids = job.get("artifacts", [])
        if artifact_id not in artifact_ids:
            artifact_ids.append(artifact_id)
        self.store.patch("jobs", job_id, {"artifacts": artifact_ids, "updated_at": utc_now_iso()})

    def get_job(self, job_id: str) -> dict[str, Any]:
        job = self.store.get("jobs", job_id)
        if not job:
            raise ValueError(f"unknown job_id: {job_id}")
        return job

    def get_status(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        return {
            "job_id": job_id,
            "status": job.get("status"),
            "template_id": job.get("template_id"),
            "summary": _job_summary(job),
            "result": job.get("result"),
            "failure": job.get("failure"),
            "artifacts": job.get("artifacts", []),
        }

    def get_logs(self, job_id: str, tail_lines: int = 200, level: str | None = None) -> dict[str, Any]:
        job = self.get_job(job_id)
        logs = job.get("logs", [])[-tail_lines:]
        return {"job_id": job_id, "logs": logs, "level": level}

    def get_metrics(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        return {"job_id": job_id, "metrics": job.get("metrics", {})}

    def cancel_job(self, job_id: str, reason: str = "cancelled_by_client") -> dict[str, Any]:
        job = self.get_job(job_id)
        if job.get("status") not in ACTIVE_STATUSES:
            return {"job_id": job_id, "status": job.get("status"), "cancelled": False}
        self.store.patch(
            "jobs",
            job_id,
            {
                "status": JobStatus.CANCELLED.value,
                "cancel_reason": reason,
                "updated_at": utc_now_iso(),
                "ended_at": utc_now_iso(),
            },
        )
        self._append_log(job_id, f"cancel requested: {reason}")
        return {"job_id": job_id, "status": JobStatus.CANCELLED.value, "cancelled": True}

    def retry_job(self, job_id: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        job = self.get_job(job_id)
        args = dict(job.get("args", {}))
        args.update(overrides or {})
        return self.submit_job(
            template_id=job["template_id"],
            project_id=job["project_id"],
            user_id=job["user_id"],
            workspace_id=job.get("workspace_id"),
            lease_id=job.get("lease_id"),
            env_id=job.get("env_id", "llm-opt-cu124-v3"),
            args=args,
            run_id=job.get("run_id"),
            priority=job.get("priority", "normal"),
        )

    def analyze_failure(
        self, job_id: str, *, include_logs: bool = True, include_environment: bool = True
    ) -> dict[str, Any]:
        job = self.get_job(job_id)
        failure = job.get("failure") or {}
        status = job.get("status")
        if status != JobStatus.FAILED.value:
            return {
                "job_id": job_id,
                "status": status,
                "failure_type": None,
                "root_cause": "Job is not in failed state.",
                "retryable": False,
            }
        message = failure.get("message", "")
        failure_type = "unknown"
        suggested = ["retry_job with the same arguments after checking logs"]
        if "memory" in message.lower():
            failure_type = "out_of_memory"
            suggested = ["request a larger GPU lease", "reduce max sequence length", "try INT8 first"]
        details = {
            "job_id": job_id,
            "failure_type": failure_type,
            "root_cause": message or "The runner reported a template failure.",
            "retryable": True,
            "suggested_actions": suggested,
        }
        if include_logs:
            details["logs"] = job.get("logs", [])[-50:]
        if include_environment:
            details["environment"] = {"env_id": job.get("env_id"), "template_id": job.get("template_id")}
        return details

    def wait_for_job(self, job_id: str, timeout_seconds: float = 10) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            job = self.get_job(job_id)
            if job.get("status") not in ACTIVE_STATUSES:
                return job
            time.sleep(0.05)
        return self.get_job(job_id)


def _hash_args(args: dict[str, Any]) -> str:
    raw = json.dumps(args, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _rng(job_id: str, args: dict[str, Any]) -> random.Random:
    seed = int(hashlib.sha256(f"{job_id}:{_hash_args(args)}".encode()).hexdigest()[:8], 16)
    return random.Random(seed)


def _guess_architecture(name: str) -> str:
    lowered = name.lower()
    if "qwen" in lowered:
        return "qwen"
    if "llama" in lowered:
        return "llama"
    if "mistral" in lowered:
        return "mistral"
    if "bert" in lowered:
        return "bert"
    return "decoder-only-transformer"


def _job_summary(job: dict[str, Any]) -> str:
    status = job.get("status")
    template_id = job.get("template_id")
    if status == JobStatus.SUCCEEDED.value:
        return f"{template_id} completed successfully."
    if status == JobStatus.FAILED.value:
        return f"{template_id} failed."
    if status == JobStatus.WAITING_FOR_RESOURCE.value:
        return f"{template_id} is waiting for an allocated resource lease."
    return f"{template_id} is {status}."
