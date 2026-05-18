# Contributing

Thanks for helping make GPU model onboarding safer and less painful.

## Development Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
ruff check .
```

## Contribution Guidelines

- Keep tools structured and safe; do not add arbitrary shell execution.
- Preserve JSON-native tool responses.
- Include tests for resource, workspace, job, or onboarding behavior.
- Update `docs/tool-reference.md` when adding tools.
- Keep simulation mode working without a GPU.
- Add production adapters behind explicit configuration.

## Pull Request Checklist

- Tests pass locally.
- New tools include docstrings.
- New production behavior has a safety note.
- Artifact lineage is preserved.
- README/docs are updated if user-facing behavior changes.

