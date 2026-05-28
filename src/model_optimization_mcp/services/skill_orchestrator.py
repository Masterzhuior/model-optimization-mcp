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
        ]
        if device_enabled:
            steps.extend(
                [
                    _hybrid_step(
                        "package-for-device-farm",
                        "local_skill",
                        "device-farm-evaluation",
                        "Generate platform packaging metadata and deployment notes.",
                    ),
                    _hybrid_step(
                        "run-device-farm",
                        "mcp_tool",
                        "device-farm-evaluation",
                        "Submit artifact to device farm and collect KPI matrix.",
                    ),
                    _hybrid_step(
                        "analyze-regression",
                        "hybrid",
                        "kpi-regression-analysis",
                        "Combine KPI report with local reasoning to propose a recipe revision.",
                    ),
                ]
            )
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

