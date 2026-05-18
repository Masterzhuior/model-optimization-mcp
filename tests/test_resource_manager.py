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
        simulation_speed=10,
        allow_simulated_gpus=True,
    )


class ResourceManagerTest(unittest.TestCase):
    def test_lease_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            ctx = create_app_context(make_settings(Path(raw)))
            snapshot = ctx.resources.snapshot(include_processes=False)
            self.assertGreaterEqual(len(snapshot["gpus"]), 1)

            lease = ctx.resources.request_lease(
                project_id="team-a",
                user_id="alice",
                purpose="baseline_eval",
                requirements={"gpu_count": 1, "gpu_memory_gb": 1, "duration_minutes": 30},
            )
            self.assertEqual(lease["status"], "allocated")
            self.assertEqual(len(lease["allocated_gpu_uuids"]), 1)

            renewed = ctx.resources.renew_lease(lease["lease_id"], duration_minutes=45)
            self.assertEqual(renewed["status"], "allocated")
            self.assertIsNotNone(renewed["expires_at"])

            released = ctx.resources.release_lease(lease["lease_id"], reason="test_done")
            self.assertEqual(released["status"], "released")


if __name__ == "__main__":
    unittest.main()
