# Security Policy

Please report security issues privately to the maintainers before public disclosure.

## Scope

Security-sensitive areas include:

- resource lease bypass,
- arbitrary filesystem access,
- arbitrary shell execution,
- unauthorized dataset/model access,
- artifact export or promotion bypass,
- cross-project metadata leakage,
- denial-of-service through unbounded GPU, disk, or job usage.

## Expected Production Controls

This repository is a reference implementation. Production deployments should add:

- enterprise authentication,
- project-level authorization,
- network TLS/mTLS,
- real quota and admission policy,
- audit log retention,
- secure artifact storage,
- approval workflow integration.

