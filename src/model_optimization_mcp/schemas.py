"""Shared schema constants and dataclass helpers.

The server deliberately keeps schemas JSON-native. This makes the tools easy to
consume from different MCP clients and avoids coupling business logic to a
specific validation framework.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class LeaseStatus(str, Enum):
    ALLOCATED = "allocated"
    QUEUED = "queued"
    RELEASED = "released"
    EXPIRED = "expired"
    REJECTED = "rejected"


class JobStatus(str, Enum):
    CREATED = "created"
    ADMITTED = "admitted"
    QUEUED = "queued"
    RESOURCE_ALLOCATED = "resource_allocated"
    PREPARING_WORKSPACE = "preparing_workspace"
    PULLING_IMAGE = "pulling_image"
    RUNNING = "running"
    COLLECTING_METRICS = "collecting_metrics"
    UPLOADING_ARTIFACTS = "uploading_artifacts"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    WAITING_FOR_RESOURCE = "waiting_for_resource"


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactStage(str, Enum):
    CANDIDATE = "candidate"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


@dataclass
class ResourceRequirement:
    gpu_count: int = 0
    gpu_memory_gb: float = 0
    cpu_cores: int = 4
    ram_gb: float = 16
    disk_gb: float = 20
    duration_minutes: int = 60
    exclusive_gpu: bool = True

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> ResourceRequirement:
        payload = payload or {}
        return cls(
            gpu_count=int(payload.get("gpu_count", 0)),
            gpu_memory_gb=float(payload.get("gpu_memory_gb", 0)),
            cpu_cores=int(payload.get("cpu_cores", 4)),
            ram_gb=float(payload.get("ram_gb", 16)),
            disk_gb=float(payload.get("disk_gb", 20)),
            duration_minutes=int(payload.get("duration_minutes", 60)),
            exclusive_gpu=bool(payload.get("exclusive_gpu", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NextAction:
    label: str
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    requires_human_input: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ok(
    summary: str,
    *,
    data: dict[str, Any] | None = None,
    next_actions: list[NextAction | dict[str, Any]] | None = None,
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    for action in next_actions or []:
        actions.append(action.to_dict() if isinstance(action, NextAction) else action)
    response: dict[str, Any] = {
        "status": "succeeded",
        "summary": summary,
    }
    if data is not None:
        response["data"] = data
    if actions:
        response["next_actions"] = actions
    return response


def failed(
    summary: str,
    *,
    failure_type: str = "unknown",
    retryable: bool = False,
    suggested_actions: list[NextAction | dict[str, Any]] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    for action in suggested_actions or []:
        actions.append(action.to_dict() if isinstance(action, NextAction) else action)
    response: dict[str, Any] = {
        "status": "failed",
        "summary": summary,
        "failure_type": failure_type,
        "retryable": retryable,
    }
    if actions:
        response["suggested_actions"] = actions
    if details:
        response["details"] = details
    return response
