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


class WorkspaceManagerTest(unittest.TestCase):
    def test_workspace_file_safety(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            ctx = create_app_context(make_settings(Path(raw)))
            ws = ctx.workspaces.create_workspace(project_id="team-a", user_id="alice")
            written = ctx.workspaces.write_config_file(
                ws["workspace_id"],
                "configs/eval.json",
                {"dataset_id": "eval-internal-chat-v2"},
            )
            self.assertEqual(written["relative_path"], "configs\\eval.json" if "\\" in written["relative_path"] else "configs/eval.json")

            read = ctx.workspaces.read_text_file(ws["workspace_id"], "configs/eval.json")
            self.assertIn("eval-internal-chat-v2", read["text"])

            with self.assertRaises(ValueError):
                ctx.workspaces.read_text_file(ws["workspace_id"], "../secrets.txt")


if __name__ == "__main__":
    unittest.main()
