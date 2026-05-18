"""GPU, queue, quota, and process governance."""

from __future__ import annotations

from typing import Any

from ..adapters.gpu import query_gpu_processes, query_nvidia_smi
from ..config import Settings
from ..schemas import LeaseStatus, ResourceRequirement
from ..store import JsonStateStore
from ..utils import disk_usage, is_future, iso_after, short_id, utc_now_iso


class ResourceManager:
    def __init__(self, store: JsonStateStore, settings: Settings):
        self.store = store
        self.settings = settings

    def _discover_gpus(self) -> list[dict[str, Any]]:
        live_gpus = query_nvidia_smi()
        if live_gpus or not self.settings.allow_simulated_gpus:
            return live_gpus
        return [
            {
                "gpu_id": 0,
                "uuid": "SIM-GPU-0000",
                "name": "Simulated H100 80GB",
                "memory_total_gb": 80.0,
                "memory_used_gb": 0.0,
                "utilization": 0.0,
                "temperature": 35,
                "source": "simulated",
            },
            {
                "gpu_id": 1,
                "uuid": "SIM-GPU-0001",
                "name": "Simulated H100 80GB",
                "memory_total_gb": 80.0,
                "memory_used_gb": 0.0,
                "utilization": 0.0,
                "temperature": 36,
                "source": "simulated",
            },
        ]

    def _active_leases(self) -> list[dict[str, Any]]:
        leases = []
        for lease in self.store.list("leases"):
            if lease.get("status") == LeaseStatus.ALLOCATED and is_future(lease.get("expires_at")):
                leases.append(lease)
        return leases

    def _allocated_gpu_uuids(self) -> set[str]:
        allocated: set[str] = set()
        for lease in self._active_leases():
            allocated.update(lease.get("allocated_gpu_uuids", []))
        return allocated

    def snapshot(
        self,
        *,
        include_processes: bool = True,
        include_jobs: bool = True,
        include_disk: bool = True,
        include_queue: bool = True,
    ) -> dict[str, Any]:
        active_by_gpu: dict[str, dict[str, Any]] = {}
        for lease in self._active_leases():
            for gpu_uuid in lease.get("allocated_gpu_uuids", []):
                active_by_gpu[gpu_uuid] = lease

        gpus = []
        for gpu in self._discover_gpus():
            lease = active_by_gpu.get(gpu["uuid"])
            enriched = dict(gpu)
            enriched["allocated_by_lease"] = lease.get("lease_id") if lease else None
            enriched["allocated_to_user"] = lease.get("user_id") if lease else None
            enriched["allocated_to_project"] = lease.get("project_id") if lease else None
            enriched["running_jobs"] = [
                job["job_id"]
                for job in self.store.list("jobs")
                if job.get("lease_id") == (lease or {}).get("lease_id")
                and job.get("status")
                in {
                    "resource_allocated",
                    "preparing_workspace",
                    "pulling_image",
                    "running",
                    "collecting_metrics",
                    "uploading_artifacts",
                }
            ]
            gpus.append(enriched)

        response: dict[str, Any] = {
            "timestamp": utc_now_iso(),
            "gpus": gpus,
            "leases": self._active_leases(),
        }
        if include_processes:
            response["gpu_processes"] = self.list_gpu_processes()
        if include_jobs:
            response["active_jobs"] = [
                job
                for job in self.store.list("jobs")
                if job.get("status")
                not in {"succeeded", "failed", "cancelled", "expired"}
            ]
        if include_disk:
            response["disk"] = {
                "workspace": disk_usage(self.settings.workspace_root),
                "cache": disk_usage(self.settings.cache_root),
                "artifacts": disk_usage(self.settings.artifact_root),
            }
        if include_queue:
            queued = [
                lease for lease in self.store.list("leases") if lease.get("status") == LeaseStatus.QUEUED
            ]
            response["queue"] = {
                "pending_leases": len(queued),
                "estimated_wait_minutes": len(queued) * 15,
                "items": queued,
            }
        return response

    def estimate_need(
        self,
        *,
        model_id: str | None = None,
        model_uri: str | None = None,
        stage: str = "quantization",
        parameter_count_b: float | None = None,
        dtype: str = "bf16",
    ) -> dict[str, Any]:
        model = self.store.get("models", model_id) if model_id else None
        params = parameter_count_b or float((model or {}).get("parameter_count_b", 7))
        dtype_factor = 2.0 if dtype.lower() in {"bf16", "fp16", "float16"} else 4.0
        raw_weight_gb = params * dtype_factor
        multipliers = {
            "inspect": 0.2,
            "load": 1.3,
            "baseline_eval": 1.5,
            "baseline_benchmark": 1.6,
            "quantization": 2.2,
            "quantized_eval": 1.1,
            "benchmark": 1.2,
            "compile": 2.0,
        }
        multiplier = multipliers.get(stage, 1.4)
        gpu_memory_gb = max(16.0, round(raw_weight_gb * multiplier, 1))
        gpu_count = 0 if stage in {"inspect", "report"} else max(1, int(gpu_memory_gb // 80) + 1)
        gpu_count = min(gpu_count, 8)
        return {
            "model_id": model_id,
            "model_uri": model_uri or (model or {}).get("model_uri"),
            "stage": stage,
            "estimated": {
                "gpu_count": gpu_count,
                "gpu_memory_gb": gpu_memory_gb,
                "cpu_cores": 16 if gpu_count else 4,
                "ram_gb": max(32, round(gpu_memory_gb * 2)),
                "disk_gb": max(100, round(params * 20)),
                "duration_minutes": 180 if stage == "quantization" else 60,
            },
            "assumptions": {
                "parameter_count_b": params,
                "dtype": dtype,
                "stage_multiplier": multiplier,
            },
        }

    def request_lease(
        self,
        *,
        project_id: str,
        user_id: str,
        purpose: str,
        requirements: dict[str, Any] | None = None,
        scheduling: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        req = ResourceRequirement.from_dict(requirements)
        scheduling = scheduling or {}
        gpus = self._discover_gpus()
        allocated = self._allocated_gpu_uuids()
        available = [
            gpu
            for gpu in gpus
            if gpu["uuid"] not in allocated and gpu["memory_total_gb"] >= req.gpu_memory_gb
        ]

        lease_id = short_id("lease")
        can_allocate = len(available) >= req.gpu_count
        should_queue = bool(scheduling.get("queue_if_unavailable", True))
        if can_allocate:
            selected = available[: req.gpu_count]
            status = LeaseStatus.ALLOCATED
        elif should_queue:
            selected = []
            status = LeaseStatus.QUEUED
        else:
            selected = []
            status = LeaseStatus.REJECTED

        lease = {
            "lease_id": lease_id,
            "status": status.value,
            "project_id": project_id,
            "user_id": user_id,
            "purpose": purpose,
            "requirements": req.to_dict(),
            "scheduling": scheduling,
            "allocated_gpus": [gpu["gpu_id"] for gpu in selected],
            "allocated_gpu_uuids": [gpu["uuid"] for gpu in selected],
            "cuda_visible_devices": ",".join(str(gpu["gpu_id"]) for gpu in selected),
            "created_at": utc_now_iso(),
            "expires_at": iso_after(req.duration_minutes) if status == LeaseStatus.ALLOCATED else None,
        }
        self.store.upsert("leases", lease_id, lease)
        return lease

    def renew_lease(self, lease_id: str, duration_minutes: int = 60) -> dict[str, Any]:
        lease = self.store.get("leases", lease_id)
        if not lease:
            raise ValueError(f"unknown lease_id: {lease_id}")
        if lease["status"] != LeaseStatus.ALLOCATED:
            raise ValueError(f"cannot renew lease in status {lease['status']}")
        lease["expires_at"] = iso_after(duration_minutes)
        lease["renewed_at"] = utc_now_iso()
        return self.store.upsert("leases", lease_id, lease)

    def release_lease(self, lease_id: str, reason: str = "released_by_client") -> dict[str, Any]:
        lease = self.store.get("leases", lease_id)
        if not lease:
            raise ValueError(f"unknown lease_id: {lease_id}")
        lease["status"] = LeaseStatus.RELEASED.value
        lease["released_at"] = utc_now_iso()
        lease["release_reason"] = reason
        return self.store.upsert("leases", lease_id, lease)

    def queue_status(self, project_id: str | None = None) -> dict[str, Any]:
        leases = [
            lease for lease in self.store.list("leases") if lease.get("status") == LeaseStatus.QUEUED
        ]
        if project_id:
            leases = [lease for lease in leases if lease.get("project_id") == project_id]
        return {
            "pending_leases": len(leases),
            "estimated_wait_minutes": len(leases) * 15,
            "items": leases,
        }

    def user_usage(self, user_id: str | None = None, project_id: str | None = None) -> dict[str, Any]:
        leases = self.store.list("leases")
        jobs = self.store.list("jobs")
        if user_id:
            leases = [lease for lease in leases if lease.get("user_id") == user_id]
            jobs = [job for job in jobs if job.get("user_id") == user_id]
        if project_id:
            leases = [lease for lease in leases if lease.get("project_id") == project_id]
            jobs = [job for job in jobs if job.get("project_id") == project_id]
        allocated = [lease for lease in leases if lease.get("status") == LeaseStatus.ALLOCATED]
        return {
            "user_id": user_id,
            "project_id": project_id,
            "lease_count": len(leases),
            "active_lease_count": len(allocated),
            "job_count": len(jobs),
            "succeeded_jobs": len([job for job in jobs if job.get("status") == "succeeded"]),
            "failed_jobs": len([job for job in jobs if job.get("status") == "failed"]),
        }

    def list_gpu_processes(self) -> list[dict[str, Any]]:
        live = query_gpu_processes()
        if live:
            return live
        processes: list[dict[str, Any]] = []
        for job in self.store.list("jobs"):
            if job.get("status") == "running":
                processes.append(
                    {
                        "pid": None,
                        "gpu_uuid": ",".join(job.get("gpu_uuids", [])),
                        "process_name": f"simulated:{job.get('template_id')}",
                        "used_memory_gb": job.get("metrics", {}).get("gpu_memory_gb", 0),
                        "job_id": job["job_id"],
                        "source": "job-store",
                    }
                )
        return processes

    def cleanup_orphan_jobs(self, dry_run: bool = True) -> dict[str, Any]:
        live_processes = self.list_gpu_processes()
        known_job_ids = {job["job_id"] for job in self.store.list("jobs")}
        orphans = [
            process
            for process in live_processes
            if process.get("job_id") and process.get("job_id") not in known_job_ids
        ]
        return {
            "dry_run": dry_run,
            "orphan_count": len(orphans),
            "orphans": orphans,
            "action": "no_processes_killed_by_design",
        }

