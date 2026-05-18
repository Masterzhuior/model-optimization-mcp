"""Small utilities shared by the server and service layer."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def iso_after(minutes: int) -> str:
    return (utc_now() + timedelta(minutes=minutes)).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def is_future(value: str | None) -> bool:
    parsed = parse_iso(value)
    return bool(parsed and parsed > utc_now())


def short_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def slugify(value: str, fallback: str = "item") -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", lowered).strip("-")
    return slug or fallback


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_join(root: Path, relative_path: str | Path) -> Path:
    root = root.resolve()
    candidate = (root / str(relative_path).lstrip("/\\")).resolve()
    if root != candidate and root not in candidate.parents:
        msg = f"path escapes managed root: {relative_path}"
        raise ValueError(msg)
    return candidate


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def file_checksum(path: Path, algorithm: str = "sha256", chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return f"{algorithm}:{digest.hexdigest()}"


def directory_size_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def disk_usage(path: Path) -> dict[str, float]:
    ensure_dir(path)
    usage = shutil.disk_usage(path)
    return {
        "total_gb": round(usage.total / 1024**3, 2),
        "used_gb": round(usage.used / 1024**3, 2),
        "free_gb": round(usage.free / 1024**3, 2),
    }


def deep_merge(base: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    if not overrides:
        return dict(base)
    result = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def public_error(exc: Exception) -> dict[str, Any]:
    return {
        "status": "failed",
        "error_type": exc.__class__.__name__,
        "message": str(exc),
    }
