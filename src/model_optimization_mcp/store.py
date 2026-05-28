"""Tiny JSON-backed state store.

This is intentionally boring and inspectable. Production deployments can replace
it with Postgres, Redis, or an internal metadata service while preserving the
same service interfaces.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from .utils import read_json, write_json

COLLECTIONS = (
    "leases",
    "jobs",
    "workspaces",
    "models",
    "datasets",
    "artifacts",
    "runs",
    "recipes",
    "runtime_envs",
    "task_templates",
    "intake_sessions",
    "recipe_specs",
    "compute_pools",
    "compute_nodes",
    "device_pools",
    "devices",
    "device_test_runs",
    "kpi_reports",
    "recipe_feedback",
    "agent_skills",
    "workflow_plans",
    "ports",
    "services",
    "audit_events",
)


class JsonStateStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        state = read_json(self.path, default={})
        for collection in COLLECTIONS:
            state.setdefault(collection, {})
        return state

    def reset(self) -> None:
        with self._lock:
            self._state = {collection: {} for collection in COLLECTIONS}
            self.save()

    def save(self) -> None:
        with self._lock:
            write_json(self.path, self._state)

    def list(self, collection: str) -> list[dict[str, Any]]:
        with self._lock:
            return [deepcopy(item) for item in self._state[collection].values()]

    def get(self, collection: str, item_id: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._state[collection].get(item_id)
            return deepcopy(item) if item is not None else None

    def upsert(self, collection: str, item_id: str, item: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._state[collection][item_id] = deepcopy(item)
            self.save()
            return deepcopy(item)

    def patch(self, collection: str, item_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            current = self._state[collection].get(item_id, {})
            current.update(deepcopy(patch))
            self._state[collection][item_id] = current
            self.save()
            return deepcopy(current)

    def delete(self, collection: str, item_id: str) -> bool:
        with self._lock:
            existed = item_id in self._state[collection]
            self._state[collection].pop(item_id, None)
            self.save()
            return existed

    def append_audit(self, event: dict[str, Any]) -> None:
        event_id = event["event_id"]
        self.upsert("audit_events", event_id, event)
