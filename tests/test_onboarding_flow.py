from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from model_optimization_mcp.app import create_app_context
from model_optimization_mcp.config import Settings


def make_settings(tmp: Path) -> Settings:
    return Settings(
        home=tmp,
        state_dir=tmp / "state",
        workspace_root=tmp / "workspaces",
        cache_root=tmp / "cache",
        artifact_root=tmp / "artifacts",
        simulation_speed=20,
        allow_simulated_gpus=True,
    )


class OnboardingFlowTest(unittest.TestCase):
    def test_guided_onboarding_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            ctx = create_app_context(make_settings(Path(raw)))
            started = ctx.onboarding.start(
                project_id="team-a",
                user_id="alice",
                model_uri="s3://models/qwen2.5-7b-instruct",
                target_hardware="H100",
            )
            run_id = started["run_id"]
            model_id = started["model_id"]
            workspace_id = started["workspace_id"]

            inspect = ctx.onboarding.run_stage(run_id=run_id, stage="inspect_model")
            inspect_job_id = inspect["job_id"]
            inspect_job = ctx.jobs.wait_for_job(inspect_job_id, timeout_seconds=5)
            self.assertEqual(inspect_job["status"], "succeeded")

            prep = ctx.onboarding.run_stage(run_id=run_id, stage="prepare_calibration")
            self.assertEqual(prep["status"], "succeeded")

            recipes = ctx.onboarding.recommend_recipes(
                model_id=model_id,
                target={"hardware": "H100", "backend": "vllm"},
                constraints={"max_accuracy_drop": 0.01, "min_speedup": 1.5},
            )
            self.assertGreaterEqual(len(recipes["recipes"]), 1)

            lease = ctx.resources.request_lease(
                project_id="team-a",
                user_id="alice",
                purpose="quantization",
                requirements={"gpu_count": 1, "gpu_memory_gb": 1, "duration_minutes": 30},
            )
            quant = ctx.jobs.submit_job(
                template_id="quantize_model_v1",
                project_id="team-a",
                user_id="alice",
                workspace_id=workspace_id,
                lease_id=lease["lease_id"],
                run_id=run_id,
                args={"model_id": model_id, "recipe_id": recipes["recipes"][0]["recipe_id"]},
            )
            quant_job = ctx.jobs.wait_for_job(quant["job_id"], timeout_seconds=5)
            self.assertEqual(quant_job["status"], "succeeded")
            self.assertTrue(quant_job["artifacts"])


if __name__ == "__main__":
    unittest.main()
