"""High-level model onboarding workflow helpers."""

from __future__ import annotations

from typing import Any

from ..schemas import NextAction, RunStatus
from ..store import JsonStateStore
from ..utils import deep_merge, short_id, utc_now_iso
from .job_manager import JobManager
from .resource_manager import ResourceManager
from .workspace_manager import WorkspaceManager

DEFAULT_STAGES = [
    "inspect_model",
    "validate_model_load",
    "prepare_calibration",
    "baseline_eval",
    "baseline_benchmark",
    "recommend_recipes",
    "quantize_candidates",
    "quantized_eval",
    "benchmark_candidates",
    "compare",
    "report",
]


STAGE_TO_TEMPLATE = {
    "inspect_model": "inspect_model_v1",
    "validate_model_load": "validate_model_load_v1",
    "baseline_eval": "baseline_eval_v1",
    "baseline_benchmark": "baseline_benchmark_v1",
    "quantization": "quantize_model_v1",
    "quantize_candidates": "quantize_model_v1",
    "quantized_eval": "quantized_eval_v1",
    "benchmark": "benchmark_v1",
    "benchmark_candidates": "benchmark_v1",
    "profile": "profile_v1",
    "compile": "compile_model_v1",
    "report": "report_v1",
}


class OnboardingManager:
    def __init__(
        self,
        store: JsonStateStore,
        resources: ResourceManager,
        workspaces: WorkspaceManager,
        jobs: JobManager,
    ):
        self.store = store
        self.resources = resources
        self.workspaces = workspaces
        self.jobs = jobs

    def start(
        self,
        *,
        project_id: str,
        user_id: str,
        model_uri: str,
        task_type: str = "text-generation",
        target_hardware: str = "H100",
        optimization_goal: dict[str, Any] | None = None,
        eval_dataset_id: str = "eval-internal-chat-v2",
        calibration_dataset_id: str = "calib-general-v1",
        name: str | None = None,
    ) -> dict[str, Any]:
        run_id = short_id("run")
        model = self.workspaces.register_model(
            project_id=project_id,
            model_uri=model_uri,
            model_name=name or model_uri.rstrip("/").split("/")[-1],
            task_type=task_type,
        )
        workspace = self.workspaces.create_workspace(
            project_id=project_id, user_id=user_id, run_id=run_id
        )
        self.workspaces.stage_model(
            workspace_id=workspace["workspace_id"], model_uri=model_uri, model_id=model["model_id"]
        )
        run = {
            "run_id": run_id,
            "name": name or model["model_name"],
            "project_id": project_id,
            "user_id": user_id,
            "model_id": model["model_id"],
            "model_uri": model_uri,
            "workspace_id": workspace["workspace_id"],
            "task_type": task_type,
            "target_hardware": target_hardware,
            "optimization_goal": optimization_goal or {
                "quantization": ["int4", "int8"],
                "max_accuracy_drop": 0.01,
                "min_speedup": 2.0,
            },
            "eval_dataset_id": eval_dataset_id,
            "calibration_dataset_id": calibration_dataset_id,
            "stages": DEFAULT_STAGES,
            "completed_stages": [],
            "status": RunStatus.CREATED.value,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "jobs": [],
            "candidates": [],
        }
        self.store.upsert("runs", run_id, run)
        return {
            "run_id": run_id,
            "status": run["status"],
            "model_id": model["model_id"],
            "workspace_id": workspace["workspace_id"],
            "next_action": NextAction(
                label="Inspect model",
                tool="run_onboarding_stage",
                arguments={"run_id": run_id, "stage": "inspect_model"},
                reason="A new run starts by inspecting model files, tokenizer, dtype, and architecture.",
            ).to_dict(),
        }

    def get_run(self, run_id: str) -> dict[str, Any]:
        run = self.store.get("runs", run_id)
        if not run:
            raise ValueError(f"unknown run_id: {run_id}")
        return run

    def run_stage(
        self,
        *,
        run_id: str,
        stage: str,
        lease_id: str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run = self.get_run(run_id)
        run["status"] = RunStatus.RUNNING.value
        args = self._stage_args(run, stage)
        args = deep_merge(args, overrides)

        if stage == "prepare_calibration":
            result = self._prepare_calibration(run, args)
            self._mark_stage(run, stage, result=result)
            return result
        if stage == "recommend_recipes":
            result = self.recommend_recipes(
                model_id=run["model_id"],
                target={"hardware": run.get("target_hardware"), "backend": "vllm"},
                constraints=run.get("optimization_goal", {}),
            )
            self._mark_stage(run, stage, result=result)
            return result
        if stage == "compare":
            result = self.compare_run(run_id)
            self._mark_stage(run, stage, result=result)
            return result

        template_id = STAGE_TO_TEMPLATE.get(stage)
        if not template_id:
            raise ValueError(f"unsupported onboarding stage: {stage}")

        if stage in {"validate_model_load", "baseline_eval", "baseline_benchmark", "quantize_candidates", "quantized_eval", "benchmark_candidates"} and not lease_id:
            estimate = self.resources.estimate_need(model_id=run["model_id"], stage=stage)
            return {
                "status": "waiting_for_resource",
                "summary": f"Stage {stage} requires a GPU lease.",
                "required_resource": estimate["estimated"],
                "next_actions": [
                    NextAction(
                        label="Request resource lease",
                        tool="request_resource_lease",
                        arguments={
                            "project_id": run["project_id"],
                            "user_id": run["user_id"],
                            "purpose": stage,
                            "requirements": estimate["estimated"],
                            "scheduling": {"queue_if_unavailable": True},
                        },
                        reason="GPU stages are only admitted with a server-issued lease.",
                    ).to_dict()
                ],
            }

        args["_stage"] = stage
        job = self.jobs.submit_job(
            template_id=template_id,
            project_id=run["project_id"],
            user_id=run["user_id"],
            workspace_id=run["workspace_id"],
            lease_id=lease_id,
            args=args,
            run_id=run_id,
        )
        run.setdefault("jobs", []).append(job["job_id"])
        self.store.upsert("runs", run_id, run)
        return {
            "status": "submitted",
            "summary": f"Submitted {stage} as {job['job_id']}.",
            "job_id": job["job_id"],
            "stage": stage,
            "next_actions": [
                NextAction(
                    label="Check job status",
                    tool="get_job_status",
                    arguments={"job_id": job["job_id"]},
                    reason="Long-running GPU stages are asynchronous.",
                ).to_dict()
            ],
        }

    def _stage_args(self, run: dict[str, Any], stage: str) -> dict[str, Any]:
        base = {
            "run_id": run["run_id"],
            "model_id": run["model_id"],
            "model_uri": run["model_uri"],
            "workspace_id": run["workspace_id"],
        }
        if stage in {"baseline_eval", "quantized_eval"}:
            base["eval_config"] = {
                "dataset_id": run["eval_dataset_id"],
                "metrics": ["accuracy", "rouge_l", "exact_match"],
                "max_samples": 5000,
            }
            base["acceptance_criteria"] = {
                "max_accuracy_drop": run.get("optimization_goal", {}).get("max_accuracy_drop", 0.01)
            }
        if stage in {"baseline_benchmark", "benchmark_candidates"}:
            base["benchmark_config"] = {
                "traffic_profile": "online-chat",
                "input_lens": [128, 512, 2048],
                "output_lens": [128, 512],
                "concurrency": [1, 8, 32],
            }
            base["min_speedup"] = run.get("optimization_goal", {}).get("min_speedup", 2.0)
        if stage == "quantize_candidates":
            recipe_id = (run.get("recommended_recipes") or ["recipe-awq-int4-g128"])[0]
            base["recipe_id"] = recipe_id
            base["artifact_name"] = f"{run.get('name', run['run_id'])}-{recipe_id}"
            base["calibration_artifact_id"] = run.get("calibration_artifact_id")
        if stage == "quantized_eval":
            candidate = self._latest_candidate(run["run_id"])
            if candidate:
                base["quant_artifact_id"] = candidate["artifact_id"]
        if stage == "benchmark_candidates":
            candidate = self._latest_candidate(run["run_id"])
            if candidate:
                base["artifact_id"] = candidate["artifact_id"]
        return base

    def _prepare_calibration(self, run: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        staged = self.workspaces.stage_dataset(
            workspace_id=run["workspace_id"],
            dataset_id=run["calibration_dataset_id"],
            usage="calibration",
            sample_count=int(args.get("sample_count", 1024)),
        )
        calibration_artifact_id = short_id("calib")
        run["calibration_artifact_id"] = calibration_artifact_id
        return {
            "status": "succeeded",
            "summary": "Calibration dataset staged and tokenization manifest prepared.",
            "calibration_artifact_id": calibration_artifact_id,
            "dataset": staged,
        }

    def recommend_recipes(
        self,
        *,
        model_id: str,
        target: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
        candidate_methods: list[str] | None = None,
    ) -> dict[str, Any]:
        model = self.store.get("models", model_id) or {}
        architecture = (model.get("inspection") or {}).get("architecture", model.get("model_name", "llm"))
        target = target or {}
        constraints = constraints or {}
        candidates = []
        for recipe in self.store.list("recipes"):
            method = recipe.get("method")
            if candidate_methods and method not in candidate_methods:
                continue
            recommended_for = " ".join(recipe.get("recommended_for", []))
            score = 0
            if architecture in recommended_for or "llm" in recommended_for:
                score += 2
            if str(target.get("hardware", "")).lower() in recommended_for:
                score += 2
            expected = recipe.get("expected", {})
            if expected.get("accuracy_drop", 1) <= constraints.get("max_accuracy_drop", 0.02):
                score += 1
            if expected.get("speedup", 0) >= constraints.get("min_speedup", 1.0):
                score += 1
            enriched = dict(recipe)
            enriched["score"] = score
            enriched["reason"] = _recipe_reason(recipe, target, constraints)
            candidates.append(enriched)
        candidates = sorted(candidates, key=lambda item: item["score"], reverse=True)
        return {
            "status": "succeeded",
            "model_id": model_id,
            "recipes": candidates,
            "recommended_recipe_ids": [recipe["recipe_id"] for recipe in candidates[:3]],
        }

    def compare_run(self, run_id: str) -> dict[str, Any]:
        artifacts = [
            artifact
            for artifact in self.store.list("artifacts")
            if artifact.get("lineage", {}).get("run_id") == run_id
        ]
        quantized = [artifact for artifact in artifacts if artifact.get("artifact_type") == "quantized_model"]
        ranking = sorted(
            quantized,
            key=lambda item: (
                item.get("metadata", {}).get("eval", {}).get("accuracy_drop", 99),
                -item.get("metadata", {}).get("benchmark", {}).get("speedup", 0),
            ),
        )
        return {
            "status": "succeeded",
            "run_id": run_id,
            "ranking": [
                {
                    "artifact_id": artifact["artifact_id"],
                    "name": artifact.get("name"),
                    "accuracy_drop": artifact.get("metadata", {})
                    .get("eval", {})
                    .get("accuracy_drop"),
                    "speedup": artifact.get("metadata", {}).get("benchmark", {}).get("speedup"),
                    "stage": artifact.get("stage"),
                }
                for artifact in ranking
            ],
            "recommendation": ranking[0]["artifact_id"] if ranking else None,
        }

    def next_action(self, run_id: str) -> dict[str, Any]:
        run = self._refresh_completed_from_jobs(self.get_run(run_id))
        completed = set(run.get("completed_stages", []))
        for stage in run.get("stages", DEFAULT_STAGES):
            if stage not in completed:
                action = NextAction(
                    label=f"Run {stage}",
                    tool="run_onboarding_stage",
                    arguments={"run_id": run_id, "stage": stage},
                    reason=f"{stage} is the next incomplete onboarding stage.",
                )
                return {
                    "run_id": run_id,
                    "status": run.get("status"),
                    "recommended_action": action.to_dict(),
                    "requires_human_input": False,
                }
        return {
            "run_id": run_id,
            "status": RunStatus.SUCCEEDED.value,
            "recommended_action": None,
            "requires_human_input": False,
        }

    def summarize(self, run_id: str) -> dict[str, Any]:
        run = self._refresh_completed_from_jobs(self.get_run(run_id))
        jobs = [self.store.get("jobs", job_id) for job_id in run.get("jobs", [])]
        artifacts = [
            artifact
            for artifact in self.store.list("artifacts")
            if artifact.get("lineage", {}).get("run_id") == run_id
        ]
        return {
            "run": run,
            "jobs": [job for job in jobs if job],
            "artifacts": artifacts,
            "next_action": self.next_action(run_id).get("recommended_action"),
        }

    def _mark_stage(
        self, run: dict[str, Any], stage: str, result: dict[str, Any] | None = None
    ) -> None:
        completed = set(run.get("completed_stages", []))
        completed.add(stage)
        run["completed_stages"] = list(completed)
        run["updated_at"] = utc_now_iso()
        if stage == "recommend_recipes" and result:
            run["recommended_recipes"] = result.get("recommended_recipe_ids", [])
        self.store.upsert("runs", run["run_id"], run)

    def _latest_candidate(self, run_id: str) -> dict[str, Any] | None:
        candidates = [
            artifact
            for artifact in self.store.list("artifacts")
            if artifact.get("artifact_type") == "quantized_model"
            and artifact.get("lineage", {}).get("run_id") == run_id
        ]
        return candidates[-1] if candidates else None

    def _refresh_completed_from_jobs(self, run: dict[str, Any]) -> dict[str, Any]:
        completed = set(run.get("completed_stages", []))
        changed = False
        for job_id in run.get("jobs", []):
            job = self.store.get("jobs", job_id)
            if not job or job.get("status") != "succeeded":
                continue
            stage = job.get("args", {}).get("_stage")
            if stage and stage not in completed:
                completed.add(stage)
                changed = True
        if changed:
            run["completed_stages"] = list(completed)
            if set(run.get("stages", DEFAULT_STAGES)).issubset(completed):
                run["status"] = RunStatus.SUCCEEDED.value
            run["updated_at"] = utc_now_iso()
            self.store.upsert("runs", run["run_id"], run)
        return run


def _recipe_reason(
    recipe: dict[str, Any], target: dict[str, Any], constraints: dict[str, Any]
) -> str:
    method = recipe.get("method")
    expected = recipe.get("expected", {})
    return (
        f"{method} is expected to deliver about {expected.get('speedup')}x speedup with "
        f"{expected.get('accuracy_drop')} accuracy drop on target {target.get('hardware', 'unknown')} "
        f"under constraints {constraints or '{}'}."
    )
