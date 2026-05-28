"""Application wiring for services used by the MCP server and tests."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .services.artifacts import ArtifactManager
from .services.catalog import seed_catalog
from .services.control_plane import ControlPlane
from .services.device_farm import DeviceFarm
from .services.intent_planner import IntentPlanner
from .services.job_manager import JobManager
from .services.onboarding import OnboardingManager
from .services.resource_manager import ResourceManager
from .services.skill_orchestrator import SkillOrchestrator
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
    intent_planner: IntentPlanner
    control_plane: ControlPlane
    device_farm: DeviceFarm
    skill_orchestrator: SkillOrchestrator


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
    intent_planner = IntentPlanner(store)
    control_plane = ControlPlane(store)
    device_farm = DeviceFarm(store)
    skill_orchestrator = SkillOrchestrator(store)
    return AppContext(
        settings=settings,
        store=store,
        resources=resources,
        workspaces=workspaces,
        artifacts=artifacts,
        jobs=jobs,
        onboarding=onboarding,
        intent_planner=intent_planner,
        control_plane=control_plane,
        device_farm=device_farm,
        skill_orchestrator=skill_orchestrator,
    )
