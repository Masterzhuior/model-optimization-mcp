"""Hybrid workflow planning for local skills and MCP tools."""

from __future__ import annotations

from typing import Any

from ..store import JsonStateStore
from ..utils import short_id, utc_now_iso


class SkillOrchestrator:
    def __init__(self, store: JsonStateStore):
        self.store = store

    def list_skills(self, *, executor: str | None = None) -> dict[str, Any]:
        skills = self.store.list("agent_skills")
        if executor:
            skills = [skill for skill in skills if skill.get("executor") == executor]
        return {"skills": skills, "count": len(skills)}

    def get_skill(self, *, skill_id: str) -> dict[str, Any]:
        skill = self.store.get("agent_skills", skill_id)
        if not skill:
            raise ValueError(f"unknown skill_id: {skill_id}")
        return skill

    def generate_hybrid_plan(
        self,
        *,
        recipe_id: str | None = None,
        session_id: str | None = None,
        include_device_farm: bool | None = None,
    ) -> dict[str, Any]:
        recipe = self.store.get("recipe_specs", recipe_id) if recipe_id else None
        session = self.store.get("intake_sessions", session_id) if session_id else None
        if recipe_id and not recipe:
            raise ValueError(f"unknown recipe_id: {recipe_id}")
        if session_id and not session:
            raise ValueError(f"unknown session_id: {session_id}")

        device_enabled = include_device_farm
        if device_enabled is None and recipe:
            device_enabled = bool(recipe.get("spec", {}).get("device_farm", {}).get("enabled"))

        # v2: Detect platform vendor for platform-specific workflow steps
        platform_spec = (recipe or {}).get("spec", {}).get("platform", {}) if recipe else {}
        vendor = platform_spec.get("vendor")
        platform_id = platform_spec.get("platform_id")
        is_mobile = bool(vendor)

        plan_id = short_id("hplan")
        steps = [
            _hybrid_step(
                "understand-intent",
                "local_skill",
                "intent-intake",
                "Clarify ambiguous natural-language requirements before creating a recipe.",
            ),
            _hybrid_step(
                "draft-recipe",
                "local_skill",
                "recipe-authoring",
                "Create or refine the quantization recipe spec and explain tradeoffs.",
            ),
            _hybrid_step(
                "persist-and-validate-recipe",
                "mcp_tool",
                "recipe-authoring",
                "Use synthesize/validate recipe tools so the control plane has auditable state.",
            ),
        ]

        # v2: Insert platform-specific conversion steps before GPU execution
        if vendor == "mediatek":
            steps.extend([
                _hybrid_step(
                    "platform-conversion-mediatek",
                    "mcp_tool",
                    "platform-conversion-mediatek",
                    f"Convert model using MediaTek NeuroPilot toolchain for {platform_id or 'Dimensity'} NPU.",
                ),
                _hybrid_step(
                    "platform-compile-mediatek",
                    "mcp_tool",
                    "platform-conversion-mediatek",
                    "Compile quantized TFLite to DLA format using ncc-tflite.",
                ),
            ])
        elif vendor == "qualcomm":
            steps.extend([
                _hybrid_step(
                    "platform-conversion-qualcomm",
                    "mcp_tool",
                    "platform-conversion-qualcomm",
                    f"Convert model using Qualcomm QNN SDK for {platform_id or 'Snapdragon'} HTP.",
                ),
                _hybrid_step(
                    "platform-compile-qualcomm",
                    "mcp_tool",
                    "platform-conversion-qualcomm",
                    "Generate QNN context binary for HTP backend.",
                ),
            ])

        # Standard GPU steps (server-side quantization still needed for calibration)
        steps.extend([
            _hybrid_step(
                "plan-capacity",
                "mcp_tool",
                "gpu-capacity-planning",
                "Select a compute pool and estimate resource needs.",
            ),
            _hybrid_step(
                "approve-expensive-work",
                "human_approval",
                "recipe-authoring",
                "Ask for human approval if policy requires GPU budget or data access approval.",
            ),
            _hybrid_step(
                "execute-ptq",
                "mcp_tool",
                "ptq-execution",
                "Acquire lease, run quantization, run eval, and run benchmark.",
            ),
        ])

        if device_enabled:
            steps.extend([
                _hybrid_step(
                    "package-for-device-farm",
                    "local_skill",
                    "device-farm-evaluation",
                    "Generate platform packaging metadata and deployment notes.",
                ),
            ])

            # v2: Select device farm adapter based on platform
            if vendor == "aws" or (recipe or {}).get("spec", {}).get("device_farm", {}).get("platform") == "aws-device-farm":
                steps.append(_hybrid_step(
                    "run-aws-device-farm",
                    "mcp_tool",
                    "device-farm-aws",
                    "Submit artifact to AWS Device Farm and collect device pool results.",
                ))
            else:
                steps.append(_hybrid_step(
                    "run-device-farm",
                    "mcp_tool",
                    "device-farm-evaluation",
                    "Submit artifact to device farm and collect KPI matrix.",
                ))

            # v2: Platform-aware failure analysis
            steps.extend([
                _hybrid_step(
                    "analyze-regression",
                    "hybrid",
                    "platform-failure-analysis" if is_mobile else "kpi-regression-analysis",
                    "Analyze KPI failures with platform-specific remediation strategies.",
                ),
            ])

            # v2: Platform profiling if vendor is specified
            if vendor in {"mediatek", "qualcomm"}:
                steps.append(_hybrid_step(
                    "platform-profiling",
                    "mcp_tool",
                    "platform-profiling",
                    f"Collect profiling data using {vendor}-specific profiling tools.",
                ))

        steps.append(
            _hybrid_step(
                "publish-report",
                "hybrid",
                "release-reporting",
                "Generate final report, artifact lineage, risks, and promotion recommendation.",
            )
        )
        plan = {
            "workflow_plan_id": plan_id,
            "recipe_id": recipe_id,
            "session_id": session_id,
            "status": "draft",
            "created_at": utc_now_iso(),
            "steps": steps,
            # v2: Platform metadata in plan
            "platform": {
                "vendor": vendor,
                "platform_id": platform_id,
                "is_mobile": is_mobile,
            } if vendor else None,
        }
        self.store.upsert("workflow_plans", plan_id, plan)
        return plan


def _hybrid_step(step_id: str, executor: str, skill_id: str, description: str) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "executor": executor,
        "skill_id": skill_id,
        "description": description,
        "status": "pending",
    }

