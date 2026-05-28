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


class IntakeRecipeDeviceLoopTest(unittest.TestCase):
    def test_recipe_and_device_feedback_loop(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            ctx = create_app_context(make_settings(Path(raw)))
            intake = ctx.intent_planner.start_intake(
                project_id="team-mobile",
                user_id="alice",
                utterance="用 PTQ 量化 Qwen3.6 模型，目标是安卓手机端侧",
            )
            self.assertEqual(intake["status"], "needs_input")
            answered = ctx.intent_planner.answer_questions(
                session_id=intake["session_id"],
                answers={
                    "model_uri": "s3://models/qwen3.6",
                    "calibration_dataset_id": "calib-general-v1",
                    "eval_dataset_id": "eval-internal-chat-v2",
                    "deployment_target": "mobile-android",
                    "device_matrix": ["snapdragon-8gen3", "dimensity-9300"],
                    "acceptance": {
                        "max_accuracy_drop": 0.01,
                        "min_speedup": 1.5,
                        "primary_latency_ms": 32,
                        "max_memory_mb": 1400,
                    },
                },
            )
            self.assertTrue(answered["ready_for_recipe"])

            draft = ctx.intent_planner.synthesize_recipe(session_id=intake["session_id"])
            recipe_id = draft["recipe_id"]
            validation = ctx.intent_planner.validate_recipe(recipe_id=recipe_id)
            self.assertEqual(validation["status"], "succeeded")

            approved = ctx.intent_planner.approve_recipe(recipe_id=recipe_id, approver="alice")
            self.assertEqual(approved["recipe"]["status"], "approved")

            plan = ctx.control_plane.create_execution_plan_from_recipe(recipe_id=recipe_id)
            self.assertIn("device-farm-test", [step["step_id"] for step in plan["steps"]])

            artifact = ctx.artifacts.register_artifact(
                artifact_type="quantized_model",
                name="qwen3.6-int4-mobile",
                project_id="team-mobile",
                metadata={"method": "awq", "weight_bits": 4},
                lineage={"recipe_id": recipe_id},
            )
            matrix = ctx.device_farm.create_device_matrix(
                device_pool_id="mobile-device-farm-cn",
                socs=["snapdragon-8gen3", "dimensity-9300"],
            )
            run = ctx.device_farm.submit_device_test(
                artifact_id=artifact["artifact_id"],
                recipe_id=recipe_id,
                device_pool_id="mobile-device-farm-cn",
                test_matrix=matrix["matrix"],
                kpi_targets={"primary_latency_ms": 32},
            )
            report = ctx.device_farm.generate_kpi_report(
                device_test_run_id=run["device_test_run_id"],
                acceptance=approved["recipe"]["spec"]["acceptance"],
            )
            analysis = ctx.device_farm.analyze_kpi_regression(kpi_report_id=report["kpi_report_id"])
            feedback = ctx.device_farm.create_recipe_feedback(
                recipe_id=recipe_id,
                kpi_report_id=report["kpi_report_id"],
                analysis=analysis,
            )
            revision = ctx.intent_planner.create_revision_from_feedback(
                recipe_id=recipe_id,
                feedback_id=feedback["feedback_id"],
                kpi_report_id=report["kpi_report_id"],
                strategy=analysis["primary_strategy"],
            )
            self.assertEqual(revision["parent_recipe_id"], recipe_id)


if __name__ == "__main__":
    unittest.main()

