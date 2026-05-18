"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys

from .app import create_app_context
from .config import Settings
from .server import build_mcp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="model-optimization-mcp",
        description="Enterprise MCP server for GPU model onboarding and inference optimization.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="stdio",
        choices=["stdio", "http", "doctor", "reset-demo-state"],
        help="Run transport or utility command.",
    )
    parser.add_argument("--host", default=None, help="HTTP host. Defaults to MOMCP_HOST.")
    parser.add_argument("--port", type=int, default=None, help="HTTP port. Defaults to MOMCP_PORT.")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    if args.host:
        settings = settings.__class__(**{**settings.__dict__, "host": args.host})
    if args.port:
        settings = settings.__class__(**{**settings.__dict__, "port": args.port})

    context = create_app_context(settings)
    if args.command == "doctor":
        snapshot = context.resources.snapshot(
            include_processes=False, include_jobs=False, include_disk=True, include_queue=True
        )
        print(
            json.dumps(
                {
                    "status": "ok",
                    "home": str(settings.home),
                    "state": str(settings.state_dir / "state.json"),
                    "runtime_envs": len(context.store.list("runtime_envs")),
                    "recipes": len(context.store.list("recipes")),
                    "gpus": snapshot["gpus"],
                    "disk": snapshot["disk"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "reset-demo-state":
        context.store.reset()
        from .services.catalog import seed_catalog

        seed_catalog(context.store)
        print("Demo state reset.")
        return 0

    mcp = build_mcp(context)
    if args.command == "http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
