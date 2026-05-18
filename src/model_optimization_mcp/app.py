"""Application wiring for services used by the MCP server and tests."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .services.artifacts import ArtifactManager
from .services.catalog import seed_catalog
from .services.job_manager import JobManager
from .services.onboarding import OnboardingManager
from .services.resource_manager import ResourceManager
from .services.workspace_manager import WorkspaceManager
from .store import JsonStateStore


@dataclass
class AppContext:
    settings: Settings
    store: JsonStateStore
    resources: ResourceManager
    workspaces: WorkspaceManager
    artifacts: ArtifactManager
    jobs: JobManager
    onboarding: OnboardingManager


def create_app_context(settings: Settings | None = None) -> AppContext:
    settings = settings or Settings.from_env()
    settings.ensure_directories()
    store = JsonStateStore(settings.state_dir / "state.json")
    seed_catalog(store)
    artifacts = ArtifactManager(store, settings)
    resources = ResourceManager(store, settings)
    workspaces = WorkspaceManager(store, settings)
    jobs = JobManager(store, settings, artifacts)
    onboarding = OnboardingManager(store, resources, workspaces, jobs)
    return AppContext(
        settings=settings,
        store=store,
        resources=resources,
        workspaces=workspaces,
        artifacts=artifacts,
        jobs=jobs,
        onboarding=onboarding,
    )

