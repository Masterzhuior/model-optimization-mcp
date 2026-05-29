"""Tests for platform-aware functionality."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from model_optimization_mcp.app import create_app_context
from model_optimization_mcp.config import Settings
from model_optimization_mcp.services.intent_planner import _extract_intent


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


class PlatformAwareIntentTest(unittest.TestCase):
    """Test platform-aware intent extraction."""

    def test_mediatek_detection_chinese(self) -> None:
        result = _extract_intent("用 PTQ 量化 Qwen3.6 到天玑9400")
        self.assertEqual(result["vendor_hint"], "mediatek")
        self.assertEqual(result["platform_id_hint"], "mediatek-dimensity-9400")

    def test_qualcomm_detection_chinese(self) -> None:
        result = _extract_intent("量化 Llama 到骁龙8gen3 离线推理")
        self.assertEqual(result["vendor_hint"], "qualcomm")
        self.assertEqual(result["platform_id_hint"], "qualcomm-snapdragon-8gen3")
        self.assertEqual(result["inference_path"], "offline")

    def test_mediatek_detection_english(self) -> None:
        result = _extract_intent("Convert Qwen3 to INT8 for Dimensity 9300")
        self.assertEqual(result["vendor_hint"], "mediatek")

    def test_qualcomm_detection_english(self) -> None:
        result = _extract_intent("Quantize model for Snapdragon 8 Gen 3")
        self.assertEqual(result["vendor_hint"], "qualcomm")

    def test_no_vendor_hint(self) -> None:
        result = _extract_intent("Quantize model for mobile Android")
        self.assertIsNone(result["vendor_hint"])
        self.assertIsNone(result["platform_id_hint"])

    def test_inference_path_offline(self) -> None:
        result = _extract_intent("编译为DLA离线推理")
        self.assertEqual(result["inference_path"], "offline")

    def test_inference_path_online(self) -> None:
        result = _extract_intent("用TFLite在线推理")
        self.assertEqual(result["inference_path"], "online")


class PlatformAwareDeviceMatrixTest(unittest.TestCase):
    """Test platform-aware device matrix generation."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.ctx = create_app_context(make_settings(Path(self.tmpdir)))

    def test_vendor_filter_mediatek(self) -> None:
        result = self.ctx.device_farm.create_platform_aware_device_matrix(
            device_pool_id="mobile-device-farm-cn",
            vendor="mediatek",
        )
        self.assertGreater(result["total_matching"], 0)
        for device in result["matrix"]:
            self.assertEqual(device["vendor"], "mediatek")

    def test_vendor_filter_qualcomm(self) -> None:
        result = self.ctx.device_farm.create_platform_aware_device_matrix(
            device_pool_id="mobile-device-farm-cn",
            vendor="qualcomm",
        )
        self.assertGreater(result["total_matching"], 0)
        for device in result["matrix"]:
            self.assertEqual(device["vendor"], "qualcomm")

    def test_coverage_strategy_representative(self) -> None:
        result = self.ctx.device_farm.create_platform_aware_device_matrix(
            device_pool_id="mobile-device-farm-cn",
            coverage_strategy="representative",
        )
        # Should have one device per unique SoC
        socs = [d["soc"] for d in result["matrix"]]
        self.assertEqual(len(socs), len(set(socs)))


class PlatformAwareWorkflowTest(unittest.TestCase):
    """Test platform-aware workflow plan generation."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.ctx = create_app_context(make_settings(Path(self.tmpdir)))

    def test_mediatek_workflow_steps(self) -> None:
        # Create a MediaTek recipe
        recipe = {
            "recipe_id": "qr-test-mtk",
            "project_id": "test",
            "user_id": "test",
            "status": "draft",
            "spec": {
                "platform": {
                    "vendor": "mediatek",
                    "platform_id": "mediatek-dimensity-9400",
                },
                "device_farm": {"enabled": True},
            },
        }
        self.ctx.store.upsert("recipe_specs", "qr-test-mtk", recipe)

        plan = self.ctx.skill_orchestrator.generate_hybrid_plan(recipe_id="qr-test-mtk")
        step_ids = [s["step_id"] for s in plan["steps"]]

        self.assertIn("platform-conversion-mediatek", step_ids)
        self.assertIn("platform-compile-mediatek", step_ids)
        self.assertIn("platform-profiling", step_ids)

    def test_qualcomm_workflow_steps(self) -> None:
        recipe = {
            "recipe_id": "qr-test-qc",
            "project_id": "test",
            "user_id": "test",
            "status": "draft",
            "spec": {
                "platform": {
                    "vendor": "qualcomm",
                    "platform_id": "qualcomm-snapdragon-8gen3",
                },
                "device_farm": {"enabled": True},
            },
        }
        self.ctx.store.upsert("recipe_specs", "qr-test-qc", recipe)

        plan = self.ctx.skill_orchestrator.generate_hybrid_plan(recipe_id="qr-test-qc")
        step_ids = [s["step_id"] for s in plan["steps"]]

        self.assertIn("platform-conversion-qualcomm", step_ids)
        self.assertIn("platform-compile-qualcomm", step_ids)
        self.assertIn("platform-profiling", step_ids)


if __name__ == "__main__":
    unittest.main()
