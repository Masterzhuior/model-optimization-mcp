"""Workspace, model staging, dataset staging, and safe file helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ..config import Settings
from ..store import JsonStateStore
from ..utils import (
    directory_size_bytes,
    ensure_dir,
    file_checksum,
    safe_join,
    short_id,
    slugify,
    utc_now_iso,
)


class WorkspaceManager:
    def __init__(self, store: JsonStateStore, settings: Settings):
        self.store = store
        self.settings = settings

    def create_workspace(
        self,
        *,
        project_id: str,
        user_id: str,
        run_id: str | None = None,
        quota_gb: float = 500,
        purpose: str = "model-onboarding",
    ) -> dict[str, Any]:
        workspace_id = short_id("ws")
        run_component = slugify(run_id or workspace_id)
        path = self.settings.workspace_root / slugify(project_id) / run_component
        for child in ("model", "dataset", "configs", "logs", "outputs", "reports"):
            ensure_dir(path / child)
        workspace = {
            "workspace_id": workspace_id,
            "project_id": project_id,
            "user_id": user_id,
            "run_id": run_id,
            "purpose": purpose,
            "path": str(path),
            "quota_gb": quota_gb,
            "created_at": utc_now_iso(),
            "status": "active",
            "subdirs": {
                "model": str(path / "model"),
                "dataset": str(path / "dataset"),
                "configs": str(path / "configs"),
                "logs": str(path / "logs"),
                "outputs": str(path / "outputs"),
                "reports": str(path / "reports"),
            },
        }
        self.store.upsert("workspaces", workspace_id, workspace)
        return workspace

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        workspace = self.store.get("workspaces", workspace_id)
        if not workspace:
            raise ValueError(f"unknown workspace_id: {workspace_id}")
        return workspace

    def _workspace_path(self, workspace_id: str) -> Path:
        return Path(self.get_workspace(workspace_id)["path"]).resolve()

    def list_files(self, workspace_id: str, relative_path: str = ".", max_entries: int = 200) -> dict[str, Any]:
        root = self._workspace_path(workspace_id)
        target = safe_join(root, relative_path)
        if not target.exists():
            raise ValueError(f"path does not exist in workspace: {relative_path}")
        entries = []
        for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name))[:max_entries]:
            entries.append(
                {
                    "name": item.name,
                    "relative_path": str(item.relative_to(root)),
                    "type": "directory" if item.is_dir() else "file",
                    "size_bytes": item.stat().st_size if item.is_file() else None,
                    "modified_at": item.stat().st_mtime,
                }
            )
        return {
            "workspace_id": workspace_id,
            "relative_path": relative_path,
            "entries": entries,
        }

    def read_text_file(
        self, workspace_id: str, relative_path: str, max_bytes: int = 128_000
    ) -> dict[str, Any]:
        root = self._workspace_path(workspace_id)
        target = safe_join(root, relative_path)
        if not target.is_file():
            raise ValueError(f"not a readable file in workspace: {relative_path}")
        data = target.read_bytes()[:max_bytes]
        return {
            "workspace_id": workspace_id,
            "relative_path": relative_path,
            "truncated": target.stat().st_size > max_bytes,
            "text": data.decode("utf-8", errors="replace"),
        }

    def write_config_file(
        self,
        workspace_id: str,
        relative_path: str,
        content: dict[str, Any] | str,
        *,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        root = self._workspace_path(workspace_id)
        target = safe_join(root, relative_path)
        if target.suffix.lower() not in {".json", ".yaml", ".yml", ".toml", ".txt", ".md"}:
            raise ValueError("only config/text files are writable through this tool")
        if target.exists() and not overwrite:
            raise ValueError(f"file already exists: {relative_path}")
        ensure_dir(target.parent)
        if isinstance(content, dict):
            text = json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True)
        else:
            text = content
        target.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
        return {
            "workspace_id": workspace_id,
            "relative_path": str(target.relative_to(root)),
            "bytes": target.stat().st_size,
        }

    def register_model(
        self,
        *,
        project_id: str,
        model_uri: str,
        model_name: str | None = None,
        framework_hint: str = "transformers",
        task_type: str = "text-generation",
        parameter_count_b: float | None = None,
    ) -> dict[str, Any]:
        model_id = short_id("model")
        model_name = model_name or slugify(model_uri.split("/")[-1], "model")
        model = {
            "model_id": model_id,
            "project_id": project_id,
            "model_uri": model_uri,
            "model_name": model_name,
            "framework_hint": framework_hint,
            "task_type": task_type,
            "parameter_count_b": parameter_count_b or _guess_parameter_count(model_name),
            "status": "registered",
            "created_at": utc_now_iso(),
        }
        self.store.upsert("models", model_id, model)
        return model

    def stage_model(
        self,
        *,
        workspace_id: str,
        model_uri: str,
        model_id: str | None = None,
        copy_mode: str = "reference",
    ) -> dict[str, Any]:
        workspace = self.get_workspace(workspace_id)
        model_dir = Path(workspace["subdirs"]["model"])
        ensure_dir(model_dir)
        manifest = {
            "model_uri": model_uri,
            "model_id": model_id,
            "copy_mode": copy_mode,
            "staged_at": utc_now_iso(),
            "note": "Reference staging is used by default. Replace with S3/NFS/HF mirror adapters in production.",
        }
        (model_dir / "MODEL_MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if model_id:
            self.store.patch("models", model_id, {"workspace_id": workspace_id, "status": "staged"})
        return {
            "workspace_id": workspace_id,
            "model_dir": str(model_dir),
            "manifest": manifest,
        }

    def stage_dataset(
        self,
        *,
        workspace_id: str,
        dataset_id: str,
        usage: str = "evaluation",
        sample_count: int | None = None,
    ) -> dict[str, Any]:
        workspace = self.get_workspace(workspace_id)
        dataset = self.store.get("datasets", dataset_id)
        if not dataset:
            raise ValueError(f"unknown dataset_id: {dataset_id}")
        dataset_dir = Path(workspace["subdirs"]["dataset"]) / slugify(dataset_id)
        ensure_dir(dataset_dir)
        manifest = {
            "dataset_id": dataset_id,
            "usage": usage,
            "sample_count": sample_count or dataset.get("sample_count"),
            "source_uri": dataset.get("uri"),
            "staged_at": utc_now_iso(),
        }
        (dataset_dir / "DATASET_MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return {
            "workspace_id": workspace_id,
            "dataset_dir": str(dataset_dir),
            "manifest": manifest,
        }

    def compute_checksum(self, workspace_id: str, relative_path: str) -> dict[str, Any]:
        root = self._workspace_path(workspace_id)
        target = safe_join(root, relative_path)
        if target.is_file():
            checksum = file_checksum(target)
            return {"type": "file", "relative_path": relative_path, "checksum": checksum}
        if target.is_dir():
            files = []
            for item in sorted(target.rglob("*")):
                if item.is_file():
                    files.append(
                        {
                            "relative_path": str(item.relative_to(root)),
                            "checksum": file_checksum(item),
                        }
                    )
            return {"type": "directory", "relative_path": relative_path, "files": files}
        raise ValueError(f"path does not exist: {relative_path}")

    def disk_usage(self, workspace_id: str) -> dict[str, Any]:
        workspace = self.get_workspace(workspace_id)
        path = Path(workspace["path"])
        used_gb = round(directory_size_bytes(path) / 1024**3, 3)
        return {
            "workspace_id": workspace_id,
            "path": str(path),
            "used_gb": used_gb,
            "quota_gb": workspace.get("quota_gb"),
            "quota_remaining_gb": round(float(workspace.get("quota_gb", 0)) - used_gb, 3),
        }

    def cleanup_workspace(
        self, workspace_id: str, *, mode: str = "outputs-only", dry_run: bool = True
    ) -> dict[str, Any]:
        workspace = self.get_workspace(workspace_id)
        root = Path(workspace["path"])
        if mode == "outputs-only":
            targets = [root / "outputs", root / "logs"]
        elif mode == "all":
            targets = [root]
        else:
            raise ValueError("mode must be 'outputs-only' or 'all'")

        planned = []
        for target in targets:
            if target.exists():
                planned.append({"path": str(target), "size_bytes": directory_size_bytes(target)})
        if not dry_run:
            for target in targets:
                if target == root:
                    shutil.rmtree(target, ignore_errors=True)
                    workspace["status"] = "deleted"
                    self.store.upsert("workspaces", workspace_id, workspace)
                else:
                    shutil.rmtree(target, ignore_errors=True)
                    ensure_dir(target)
        return {
            "workspace_id": workspace_id,
            "dry_run": dry_run,
            "mode": mode,
            "planned": planned,
        }


def _guess_parameter_count(name: str) -> float:
    lowered = name.lower()
    for marker in ("72b", "70b", "34b", "32b", "14b", "13b", "8b", "7b", "3b", "1.5b"):
        if marker in lowered:
            return float(marker.replace("b", ""))
    return 7.0

