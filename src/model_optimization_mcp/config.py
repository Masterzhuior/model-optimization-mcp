"""Runtime configuration for the Model Optimization MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .utils import ensure_dir


@dataclass(frozen=True)
class Settings:
    """Filesystem and transport settings.

    The defaults are intentionally local-development friendly. On a GPU server,
    set ``MOMCP_HOME`` to a persistent service directory such as
    ``/srv/model-optimization-mcp``.
    """

    home: Path
    state_dir: Path
    workspace_root: Path
    cache_root: Path
    artifact_root: Path
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    simulation_speed: float = 1.0
    allow_simulated_gpus: bool = True

    @classmethod
    def from_env(cls) -> Settings:
        home = Path(os.getenv("MOMCP_HOME", ".momcp")).expanduser().resolve()
        return cls(
            home=home,
            state_dir=Path(os.getenv("MOMCP_STATE_DIR", home / "state")).expanduser().resolve(),
            workspace_root=Path(
                os.getenv("MOMCP_WORKSPACE_ROOT", home / "workspaces")
            ).expanduser().resolve(),
            cache_root=Path(os.getenv("MOMCP_CACHE_ROOT", home / "cache")).expanduser().resolve(),
            artifact_root=Path(
                os.getenv("MOMCP_ARTIFACT_ROOT", home / "artifacts")
            ).expanduser().resolve(),
            transport=os.getenv("MOMCP_TRANSPORT", "stdio"),
            host=os.getenv("MOMCP_HOST", "127.0.0.1"),
            port=int(os.getenv("MOMCP_PORT", "8000")),
            simulation_speed=float(os.getenv("MOMCP_SIMULATION_SPEED", "1.0")),
            allow_simulated_gpus=os.getenv("MOMCP_ALLOW_SIMULATED_GPUS", "true").lower()
            not in {"0", "false", "no"},
        )

    def ensure_directories(self) -> None:
        for path in (
            self.home,
            self.state_dir,
            self.workspace_root,
            self.cache_root,
            self.artifact_root,
        ):
            ensure_dir(path)

