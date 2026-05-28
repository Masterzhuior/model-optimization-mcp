"""Device-farm evaluation and KPI feedback loop."""

from __future__ import annotations

import hashlib
import random
from typing import Any

from ..store import JsonStateStore
from ..utils import short_id, utc_now_iso


class DeviceFarm:
    def __init__(self, store: JsonStateStore):
        self.store = store

    def list_device_pools(
        self,
        *,
        platform: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        pools = self.store.list("device_pools")
        if platform:
            pools = [pool for pool in pools if platform in pool.get("platforms", [])]
        if region:
            pools = [pool for pool in pools if pool.get("region") == region]
        return {"device_pools": pools, "count": len(pools)}

    def list_devices(
        self,
        *,
        device_pool_id: str | None = None,
        platform: str | None = None,
        soc: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        devices = self.store.list("devices")
        if device_pool_id:
            devices = [device for device in devices if device.get("device_pool_id") == device_pool_id]
        if platform:
            devices = [device for device in devices if device.get("platform") == platform]
        if soc:
            devices = [device for device in devices if device.get("soc") == soc]
        if status:
            devices = [device for device in devices if device.get("status") == status]
        return {"devices": devices, "count": len(devices)}

    def create_device_matrix(
        self,
        *,
        device_pool_id: str,
        socs: list[str] | None = None,
        platforms: list[str] | None = None,
        max_devices: int = 8,
    ) -> dict[str, Any]:
        devices = self.list_devices(device_pool_id=device_pool_id, status="ready")["devices"]
        if socs:
            devices = [device for device in devices if device.get("soc") in socs]
        if platforms:
            devices = [device for device in devices if device.get("platform") in platforms]
        selected = devices[:max_devices]
        return {
            "device_pool_id": device_pool_id,
            "matrix": [
                {
                    "device_id": device["device_id"],
                    "platform": device["platform"],
                    "soc": device["soc"],
                    "accelerators": device.get("accelerators", []),
                    "os_version": device.get("os_version"),
                }
                for device in selected
            ],
        }

    def submit_device_test(
        self,
        *,
        artifact_id: str,
        recipe_id: str,
        device_pool_id: str,
        test_matrix: list[dict[str, Any]],
        kpi_targets: dict[str, Any] | None = None,
        test_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        artifact = self.store.get("artifacts", artifact_id)
        if not artifact:
            raise ValueError(f"unknown artifact_id: {artifact_id}")
        recipe = self.store.get("recipe_specs", recipe_id)
        if not recipe:
            raise ValueError(f"unknown recipe_id: {recipe_id}")
        run_id = short_id("dtest")
        results = [_simulate_device_result(run_id, item, kpi_targets or {}) for item in test_matrix]
        status = "succeeded"
        test_run = {
            "device_test_run_id": run_id,
            "artifact_id": artifact_id,
            "recipe_id": recipe_id,
            "project_id": artifact["project_id"],
            "device_pool_id": device_pool_id,
            "test_matrix": test_matrix,
            "kpi_targets": kpi_targets or {},
            "test_config": test_config or {},
            "status": status,
            "created_at": utc_now_iso(),
            "started_at": utc_now_iso(),
            "ended_at": utc_now_iso(),
            "results": results,
        }
        self.store.upsert("device_test_runs", run_id, test_run)
        return test_run

    def get_device_test_status(self, *, device_test_run_id: str) -> dict[str, Any]:
        run = self.store.get("device_test_runs", device_test_run_id)
        if not run:
            raise ValueError(f"unknown device_test_run_id: {device_test_run_id}")
        return run

    def generate_kpi_report(
        self,
        *,
        device_test_run_id: str,
        acceptance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run = self.get_device_test_status(device_test_run_id=device_test_run_id)
        acceptance = acceptance or (self.store.get("recipe_specs", run["recipe_id"]) or {}).get("spec", {}).get(
            "acceptance", {}
        )
        failures = []
        summary = {
            "device_count": len(run.get("results", [])),
            "pass_count": 0,
            "fail_count": 0,
            "worst_accuracy_drop": 0.0,
            "worst_latency_p95_ms": 0.0,
            "worst_memory_peak_mb": 0,
            "worst_power_mw": 0,
        }
        for result in run.get("results", []):
            verdict = _evaluate_result(result, acceptance)
            result["verdict"] = verdict
            if verdict["pass"]:
                summary["pass_count"] += 1
            else:
                summary["fail_count"] += 1
                failures.append(result)
            summary["worst_accuracy_drop"] = max(summary["worst_accuracy_drop"], result["accuracy_drop"])
            summary["worst_latency_p95_ms"] = max(summary["worst_latency_p95_ms"], result["latency_p95_ms"])
            summary["worst_memory_peak_mb"] = max(summary["worst_memory_peak_mb"], result["memory_peak_mb"])
            summary["worst_power_mw"] = max(summary["worst_power_mw"], result["power_mw"])
        report_id = short_id("kpi")
        report = {
            "kpi_report_id": report_id,
            "device_test_run_id": device_test_run_id,
            "artifact_id": run["artifact_id"],
            "recipe_id": run["recipe_id"],
            "project_id": run["project_id"],
            "acceptance": acceptance,
            "summary": summary,
            "failures": failures,
            "status": "failed" if failures else "passed",
            "created_at": utc_now_iso(),
        }
        self.store.upsert("kpi_reports", report_id, report)
        return report

    def analyze_kpi_regression(self, *, kpi_report_id: str) -> dict[str, Any]:
        report = self.store.get("kpi_reports", kpi_report_id)
        if not report:
            raise ValueError(f"unknown kpi_report_id: {kpi_report_id}")
        failures = report.get("failures", [])
        root_causes: list[dict[str, Any]] = []
        for failure in failures:
            reasons = failure.get("verdict", {}).get("failed_kpis", [])
            if "accuracy_drop" in reasons:
                root_causes.append(
                    {
                        "type": "accuracy_regression",
                        "device_id": failure["device_id"],
                        "hypothesis": "Calibration set is not representative or sensitive layers need mixed precision.",
                        "recommended_recipe_strategy": "accuracy_regression",
                    }
                )
            if "latency_p95_ms" in reasons:
                root_causes.append(
                    {
                        "type": "latency_regression",
                        "device_id": failure["device_id"],
                        "hypothesis": "Backend kernel or delegate selection is inefficient on this SoC.",
                        "recommended_recipe_strategy": "latency_regression",
                    }
                )
            if "memory_peak_mb" in reasons:
                root_causes.append(
                    {
                        "type": "memory_regression",
                        "device_id": failure["device_id"],
                        "hypothesis": "Runtime memory planning or KV/cache strategy exceeds device budget.",
                        "recommended_recipe_strategy": "memory_regression",
                    }
                )
        if not root_causes:
            root_causes.append(
                {
                    "type": "no_regression",
                    "hypothesis": "All KPI checks passed or no actionable failure was detected.",
                    "recommended_recipe_strategy": "none",
                }
            )
        return {
            "kpi_report_id": kpi_report_id,
            "status": "analyzed",
            "root_causes": root_causes,
            "primary_strategy": root_causes[0]["recommended_recipe_strategy"],
        }

    def create_recipe_feedback(
        self,
        *,
        recipe_id: str,
        kpi_report_id: str,
        analysis: dict[str, Any] | None = None,
        author: str = "device-farm",
    ) -> dict[str, Any]:
        recipe = self.store.get("recipe_specs", recipe_id)
        if not recipe:
            raise ValueError(f"unknown recipe_id: {recipe_id}")
        report = self.store.get("kpi_reports", kpi_report_id)
        if not report:
            raise ValueError(f"unknown kpi_report_id: {kpi_report_id}")
        analysis = analysis or self.analyze_kpi_regression(kpi_report_id=kpi_report_id)
        feedback_id = short_id("feedback")
        feedback = {
            "feedback_id": feedback_id,
            "recipe_id": recipe_id,
            "kpi_report_id": kpi_report_id,
            "project_id": recipe["project_id"],
            "author": author,
            "analysis": analysis,
            "status": "open",
            "created_at": utc_now_iso(),
        }
        self.store.upsert("recipe_feedback", feedback_id, feedback)
        return feedback


def _simulate_device_result(
    run_id: str,
    device: dict[str, Any],
    targets: dict[str, Any],
) -> dict[str, Any]:
    seed = int(hashlib.sha256(f"{run_id}:{device}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    soc = device.get("soc", "unknown")
    latency_bias = 1.0
    if "kirin" in soc:
        latency_bias = 1.25
    elif "dimensity" in soc:
        latency_bias = 1.08
    accuracy_drop = round(0.004 + rng.random() * 0.012, 4)
    latency_p50 = round((18 + rng.random() * 8) * latency_bias, 2)
    latency_p95 = round(latency_p50 * (1.55 + rng.random() * 0.35), 2)
    memory_peak = int(900 + rng.random() * 850)
    power_mw = int(2100 + rng.random() * 1800)
    return {
        "device_id": device.get("device_id"),
        "platform": device.get("platform"),
        "soc": soc,
        "accuracy_drop": accuracy_drop,
        "latency_p50_ms": latency_p50,
        "latency_p95_ms": latency_p95,
        "memory_peak_mb": memory_peak,
        "power_mw": power_mw,
        "thermal_c": round(37 + rng.random() * 8, 1),
        "raw_target_hint": targets,
    }


def _evaluate_result(result: dict[str, Any], acceptance: dict[str, Any]) -> dict[str, Any]:
    failed: list[str] = []
    max_accuracy_drop = float(acceptance.get("max_accuracy_drop") or 0.01)
    if result["accuracy_drop"] > max_accuracy_drop:
        failed.append("accuracy_drop")
    latency_limit = acceptance.get("primary_latency_ms")
    if latency_limit is not None and result["latency_p95_ms"] > float(latency_limit):
        failed.append("latency_p95_ms")
    memory_limit = acceptance.get("max_memory_mb")
    if memory_limit is not None and result["memory_peak_mb"] > int(memory_limit):
        failed.append("memory_peak_mb")
    thermal_limit = acceptance.get("thermal_limit_c")
    if thermal_limit is not None and result["thermal_c"] > float(thermal_limit):
        failed.append("thermal_c")
    return {"pass": not failed, "failed_kpis": failed}

