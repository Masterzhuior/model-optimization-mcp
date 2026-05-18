"""Artifact registry and report rendering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import Settings
from ..schemas import ArtifactStage
from ..store import JsonStateStore
from ..utils import ensure_dir, short_id, slugify, utc_now_iso


class ArtifactManager:
    def __init__(self, store: JsonStateStore, settings: Settings):
        self.store = store
        self.settings = settings

    def register_artifact(
        self,
        *,
        artifact_type: str,
        name: str,
        project_id: str,
        uri: str | None = None,
        metadata: dict[str, Any] | None = None,
        lineage: dict[str, Any] | None = None,
        stage: str = ArtifactStage.CANDIDATE.value,
    ) -> dict[str, Any]:
        artifact_id = short_id("artifact")
        local_dir = self.settings.artifact_root / slugify(project_id) / artifact_id
        ensure_dir(local_dir)
        artifact = {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "name": name,
            "project_id": project_id,
            "uri": uri or f"artifact://{project_id}/{artifact_id}",
            "local_dir": str(local_dir),
            "metadata": metadata or {},
            "lineage": lineage or {},
            "stage": stage,
            "created_at": utc_now_iso(),
        }
        (local_dir / "artifact.json").write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        self.store.upsert("artifacts", artifact_id, artifact)
        return artifact

    def get_artifact(self, artifact_id: str) -> dict[str, Any]:
        artifact = self.store.get("artifacts", artifact_id)
        if not artifact:
            raise ValueError(f"unknown artifact_id: {artifact_id}")
        return artifact

    def promote_artifact(
        self,
        *,
        artifact_id: str,
        target_stage: str,
        approval_ticket: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        artifact = self.get_artifact(artifact_id)
        if target_stage == ArtifactStage.PRODUCTION and not approval_ticket:
            return {
                "status": "waiting_for_approval",
                "summary": "Production promotion requires an approval ticket.",
                "approval_reason": "Production artifact promotion is a controlled action.",
                "artifact_id": artifact_id,
            }
        artifact["stage"] = target_stage
        artifact.setdefault("promotion_history", []).append(
            {
                "target_stage": target_stage,
                "approval_ticket": approval_ticket,
                "user_id": user_id,
                "promoted_at": utc_now_iso(),
            }
        )
        self.store.upsert("artifacts", artifact_id, artifact)
        return {
            "status": "succeeded",
            "summary": f"Artifact promoted to {target_stage}.",
            "artifact": artifact,
        }

    def generate_report(
        self,
        *,
        run_id: str | None = None,
        pipeline_id: str | None = None,
        project_id: str | None = None,
        format: str = "markdown",
        include_sections: list[str] | None = None,
    ) -> dict[str, Any]:
        target_run = run_id or pipeline_id
        run = self.store.get("runs", target_run) if target_run else None
        if not run:
            raise ValueError("run_id or pipeline_id is required and must exist")
        project_id = project_id or run.get("project_id", "default")
        jobs = [job for job in self.store.list("jobs") if job.get("run_id") == target_run]
        artifacts = [
            artifact
            for artifact in self.store.list("artifacts")
            if artifact.get("lineage", {}).get("run_id") == target_run
        ]
        sections = include_sections or [
            "model_summary",
            "baseline_metrics",
            "quantization_recipes",
            "accuracy_comparison",
            "performance_comparison",
            "risk_analysis",
            "recommendation",
            "reproducibility",
        ]
        markdown = self._render_markdown_report(run, jobs, artifacts, sections)
        report_artifact = self.register_artifact(
            artifact_type="report",
            name=f"{target_run}-onboarding-report",
            project_id=project_id,
            metadata={"format": format, "sections": sections, "preview": markdown[:2000]},
            lineage={"run_id": target_run},
        )
        report_path = Path(report_artifact["local_dir"]) / "report.md"
        report_path.write_text(markdown, encoding="utf-8")
        report_artifact["uri"] = str(report_path)
        self.store.upsert("artifacts", report_artifact["artifact_id"], report_artifact)
        return {
            "report_id": report_artifact["artifact_id"],
            "run_id": target_run,
            "format": format,
            "uri": report_artifact["uri"],
            "preview": markdown,
        }

    def _render_markdown_report(
        self,
        run: dict[str, Any],
        jobs: list[dict[str, Any]],
        artifacts: list[dict[str, Any]],
        sections: list[str],
    ) -> str:
        lines = [
            f"# Model Onboarding Report: {run.get('name', run.get('run_id'))}",
            "",
            f"- Run ID: `{run.get('run_id')}`",
            f"- Project: `{run.get('project_id')}`",
            f"- Status: `{run.get('status')}`",
            f"- Created: `{run.get('created_at')}`",
            "",
        ]
        if "model_summary" in sections:
            lines.extend(
                [
                    "## Model Summary",
                    "",
                    f"- Model URI: `{run.get('model_uri')}`",
                    f"- Task type: `{run.get('task_type')}`",
                    f"- Target hardware: `{run.get('target_hardware')}`",
                    "",
                ]
            )
        if "baseline_metrics" in sections or "performance_comparison" in sections:
            lines.extend(["## Jobs", ""])
            for job in jobs:
                lines.append(
                    f"- `{job['job_id']}` `{job.get('template_id')}`: `{job.get('status')}`"
                )
            lines.append("")
        if "recommendation" in sections:
            best = _select_best_artifact(artifacts)
            lines.extend(["## Recommendation", ""])
            if best:
                lines.append(
                    f"Recommended candidate: `{best['artifact_id']}` ({best.get('name')})."
                )
            else:
                lines.append("No successful model candidate has been registered yet.")
            lines.append("")
        if "reproducibility" in sections:
            lines.extend(["## Reproducibility", ""])
            lines.append("Every job records template id, runtime env, lease id, arguments, and lineage.")
            lines.append("")
        if "risk_analysis" in sections:
            lines.extend(["## Risks", ""])
            lines.append(
                "This repository ships with a simulation runner. Replace templates with approved production adapters before handling regulated models."
            )
            lines.append("")
        return "\n".join(lines)


def _select_best_artifact(artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [artifact for artifact in artifacts if artifact.get("artifact_type") == "quantized_model"]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            item.get("metadata", {}).get("eval", {}).get("accuracy_drop", 99),
            -item.get("metadata", {}).get("benchmark", {}).get("speedup", 0),
        ),
    )[0]

