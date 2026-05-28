# Deployment Guide

## Local Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
model-optimization-mcp doctor
model-optimization-mcp stdio
```

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `MOMCP_HOME` | `.momcp` | Root service directory. |
| `MOMCP_STATE_DIR` | `$MOMCP_HOME/state` | JSON metadata store location. |
| `MOMCP_WORKSPACE_ROOT` | `$MOMCP_HOME/workspaces` | Managed workspace root. |
| `MOMCP_CACHE_ROOT` | `$MOMCP_HOME/cache` | Model/dataset/image cache root. |
| `MOMCP_ARTIFACT_ROOT` | `$MOMCP_HOME/artifacts` | Artifact storage root. |
| `MOMCP_TRANSPORT` | `stdio` | Preferred transport. |
| `MOMCP_HOST` | `127.0.0.1` | HTTP host. |
| `MOMCP_PORT` | `8000` | HTTP port. |
| `MOMCP_SIMULATION_SPEED` | `1.0` | Simulation job speed multiplier. |
| `MOMCP_ALLOW_SIMULATED_GPUS` | `true` | Use simulated GPUs when `nvidia-smi` is unavailable. |

## Streamable HTTP

```bash
MOMCP_HOME=/srv/model-optimization-mcp \
model-optimization-mcp http --host 0.0.0.0 --port 8000
```

Place this behind a gateway or reverse proxy for authentication and TLS.

## Docker

```bash
docker build -t model-optimization-mcp:local .
docker run --rm -p 8000:8000 \
  -e MOMCP_HOME=/data \
  -v "$(pwd)/.momcp:/data" \
  model-optimization-mcp:local
```

For real GPU execution, run with the NVIDIA container runtime and replace the simulation job adapter with production templates.

## Claude Desktop / Claude Code

See `examples/claude_desktop_config.json`.

## Codex

See `examples/codex_mcp_config.json`. Exact connector syntax may vary by Codex environment, but the server command is the same:

```bash
model-optimization-mcp stdio
```

## Production Hardening Checklist

- Run behind enterprise auth.
- Store metadata in Postgres.
- Store artifacts in S3/MinIO/Ceph or an internal model registry.
- Replace simulation runner with Docker/Slurm/K8s/Ray.
- Deploy GPU workers as a compute plane registered with `compute_nodes`.
- Put the MCP server behind a gateway when multiple engineer laptops connect.
- Connect `DeviceFarm` to a real phone farm API for mobile KPI validation.
- Add per-tool policy checks.
- Add approval workflow integration.
- Add metrics export to Prometheus.
- Add log shipping to your central logging system.
- Pin runtime images and quantization tool versions.
