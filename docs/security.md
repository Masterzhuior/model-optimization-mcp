# Security Model

This project assumes the local agent is helpful but not fully trusted. The MCP server is the real control boundary.

## Non-Negotiable Rules

- Do not expose arbitrary shell execution to local agents.
- Do not expose arbitrary filesystem paths.
- Do not allow agents to choose GPU IDs directly.
- Do not allow production artifact promotion without approval.
- Do not allow recipe approval bypass before expensive GPU work.
- Do not allow device-farm KPI reports to be overwritten by local agents.
- Do not allow unbounded GPU, disk, or runtime usage.
- Do not allow access to unregistered datasets or model paths.

## Server-Side Controls

### Lease Gate

Every GPU job must bind to an allocated `lease_id`. The server records:

- user,
- project,
- purpose,
- GPU UUIDs,
- TTL,
- requested resource shape,
- queue/admission decision.

### Workspace Sandbox

Workspace tools use safe path resolution and reject paths that escape the managed root. Agents can write config/text files only through the approved tool.

### Task Templates

Production systems should register task templates with:

- approved container image,
- approved entrypoint,
- JSON schema for allowed arguments,
- required resources,
- max duration,
- output artifact contract.

### Artifact Policy

Artifacts should carry sensitivity metadata. Export and promotion tools should enforce:

- project ownership,
- model license restrictions,
- regulated dataset lineage,
- approval tickets,
- audit logging.

## Gateway Recommendations

For real enterprise deployment, place this server behind an MCP gateway:

```text
Local Agent -> MCP Gateway / Control Plane -> GPU Workers + Device Farm
```

Recommended gateway features:

- SSO/OIDC,
- short-lived tokens,
- mTLS for server-to-server traffic,
- per-user/project rate limits,
- audit logs,
- tool-level policy filters,
- environment-specific tool exposure.

## Audit Events

The JSON store includes an `audit_events` collection for future policy hooks. A production implementation should emit at least:

- lease requested/allocated/released,
- recipe drafted/validated/approved/revised,
- compute node registered or heartbeat missed,
- dataset staged,
- model exported,
- device-farm test submitted,
- KPI report generated,
- recipe feedback created,
- artifact promoted,
- job submitted/cancelled/failed,
- approval requested/approved/rejected.
