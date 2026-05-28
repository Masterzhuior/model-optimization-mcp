"""Control-plane primitives for multi-node GPU execution."""

from __future__ import annotations

from typing import Any

from ..store import JsonStateStore
from ..utils import short_id, utc_now_iso


class ControlPlane:
    """Manage compute pools, GPU worker nodes, and recipe execution plans."""

    def __init__(self, store: JsonStateStore):
        self.store = store

    def list_compute_pools(
        self,
        *,
        capability: str | None = None,
        region: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        pools = self.store.list("compute_pools")
        if capability:
            pools = [pool for pool in pools if capability in pool.get("capabilities", [])]
        if region:
            pools = [pool for pool in pools if pool.get("region") == region]
        if status:
            pools = [pool for pool in pools if pool.get("status") == status]
        return {"pools": pools, "count": len(pools)}

    def list_compute_nodes(
        self,
        *,
        pool_id: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        nodes = self.store.list("compute_nodes")
        if pool_id:
            nodes = [node for node in nodes if node.get("pool_id") == pool_id]
        if status:
            nodes = [node for node in nodes if node.get("status") == status]
        return {"nodes": nodes, "count": len(nodes)}

    def register_compute_node(
        self,
        *,
        pool_id: str,
        hostname: str,
        accelerators: list[dict[str, Any]],
        cpu_cores: int,
        ram_gb: int,
        disk_gb: int,
        labels: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.store.get("compute_pools", pool_id):
            raise ValueError(f"unknown pool_id: {pool_id}")
        node_id = short_id("node")
        node = {
            "node_id": node_id,
            "pool_id": pool_id,
            "hostname": hostname,
            "accelerators": accelerators,
            "cpu_cores": cpu_cores,
            "ram_gb": ram_gb,
            "disk_gb": disk_gb,
            "labels": labels or {},
            "status": "ready",
            "registered_at": utc_now_iso(),
            "last_heartbeat_at": utc_now_iso(),
        }
        self.store.upsert("compute_nodes", node_id, node)
        return node

    def heartbeat_compute_node(
        self,
        *,
        node_id: str,
        status: str = "ready",
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        node = self.store.get("compute_nodes", node_id)
        if not node:
            raise ValueError(f"unknown node_id: {node_id}")
        node["status"] = status
        node["metrics"] = metrics or {}
        node["last_heartbeat_at"] = utc_now_iso()
        self.store.upsert("compute_nodes", node_id, node)
        return node

    def capacity_snapshot(self, *, pool_id: str | None = None) -> dict[str, Any]:
        nodes = self.list_compute_nodes(pool_id=pool_id)["nodes"]
        ready_nodes = [node for node in nodes if node.get("status") == "ready"]
        accelerators = [
            accelerator
            for node in ready_nodes
            for accelerator in node.get("accelerators", [])
        ]
        by_type: dict[str, dict[str, Any]] = {}
        for accelerator in accelerators:
            acc_type = accelerator.get("type", "unknown")
            item = by_type.setdefault(
                acc_type,
                {"type": acc_type, "count": 0, "total_memory_gb": 0},
            )
            item["count"] += 1
            item["total_memory_gb"] += accelerator.get("memory_gb", 0)
        return {
            "pool_id": pool_id,
            "node_count": len(nodes),
            "ready_node_count": len(ready_nodes),
            "accelerators": list(by_type.values()),
            "nodes": ready_nodes,
        }

    def select_compute_pool(
        self,
        *,
        recipe_id: str | None = None,
        requirements: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        requirements = requirements or {}
        recipe = self.store.get("recipe_specs", recipe_id) if recipe_id else None
        selector = (
            ((recipe or {}).get("spec") or {}).get("execution", {}).get("compute_pool_selector", {})
        )
        capability = requirements.get("capability") or selector.get("capability")
        region = requirements.get("region") or selector.get("region")
        min_gpu_memory_gb = float(requirements.get("min_gpu_memory_gb", 0))
        pools = self.list_compute_pools(capability=capability, region=region, status="ready")["pools"]
        ranked: list[dict[str, Any]] = []
        for pool in pools:
            capacity = self.capacity_snapshot(pool_id=pool["pool_id"])
            has_memory = any(
                accelerator.get("total_memory_gb", 0) >= min_gpu_memory_gb
                for accelerator in capacity["accelerators"]
            )
            score = capacity["ready_node_count"] * 10 + len(pool.get("capabilities", []))
            if min_gpu_memory_gb and not has_memory:
                score -= 100
            ranked.append({"pool": pool, "capacity": capacity, "score": score})
        ranked.sort(key=lambda item: item["score"], reverse=True)
        selected = ranked[0] if ranked else None
        return {
            "recipe_id": recipe_id,
            "selected_pool": selected["pool"] if selected else None,
            "capacity": selected["capacity"] if selected else None,
            "candidates": ranked,
        }

    def create_execution_plan_from_recipe(
        self,
        *,
        recipe_id: str,
        plan_mode: str = "full-loop",
    ) -> dict[str, Any]:
        recipe = self.store.get("recipe_specs", recipe_id)
        if not recipe:
            raise ValueError(f"unknown recipe_id: {recipe_id}")
        pool_selection = self.select_compute_pool(recipe_id=recipe_id)
        plan_id = short_id("plan")
        spec = recipe.get("spec", {})
        device_enabled = bool(spec.get("device_farm", {}).get("enabled"))
        steps = [
            _step("intent-intake", "local_skill", "Already completed by intake skill."),
            _step("recipe-authoring", "local_skill", "Explain and sanity-check the recipe with the engineer."),
            _step("recipe-validation", "mcp_tool", "validate_quantization_recipe"),
            _step("human-approval", "human_approval", "Approve recipe before expensive GPU work."),
            _step("gpu-lease", "mcp_tool", "request_resource_lease"),
            _step("ptq-execution", "mcp_tool", "run_quantization"),
            _step("server-eval", "mcp_tool", "run_quantized_eval"),
            _step("server-benchmark", "mcp_tool", "run_benchmark"),
        ]
        if device_enabled:
            steps.extend(
                [
                    _step("package-mobile-artifact", "local_skill", "Generate device-farm package metadata."),
                    _step("device-farm-test", "mcp_tool", "submit_device_farm_test"),
                    _step("kpi-report", "mcp_tool", "generate_kpi_report"),
                    _step("kpi-analysis", "hybrid", "analyze_kpi_regression"),
                    _step("recipe-feedback-loop", "mcp_tool", "create_recipe_revision_from_feedback"),
                ]
            )
        steps.append(_step("release-reporting", "hybrid", "generate_onboarding_report"))
        plan = {
            "plan_id": plan_id,
            "recipe_id": recipe_id,
            "project_id": recipe["project_id"],
            "plan_mode": plan_mode,
            "selected_compute_pool": pool_selection.get("selected_pool"),
            "steps": steps,
            "status": "draft",
            "created_at": utc_now_iso(),
        }
        self.store.upsert("workflow_plans", plan_id, plan)
        return plan


def _step(step_id: str, executor: str, instruction: str) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "executor": executor,
        "instruction": instruction,
        "status": "pending",
    }

