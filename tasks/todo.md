# Task Plan

Persistent task board for agent-assisted development.

## Current Status

- Repository baseline: `v1.0.0` released.
- Post-1.0 hardening commit pushed: request timeouts, test separation, CLI args, cache safety, export tests, and 60% coverage gate.
- Current objective: establish best-practice agent memory and skill setup.

## Active Task: Agent Memory Setup

Status: completed

Steps:

1. Create root context files: `AGENTS.md`, `CODEX.md`, `INSTRUCTIONS.md`.
2. Create durable task memory: `tasks/todo.md`, `tasks/lessons.md`.
3. Create atomic skill manuals in `skills/`.
4. Verify repository checks still pass.
5. Review diff and commit/push when complete.

Verification gates:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy .
python -m pytest -m "not integration" --cov=steamreviews --cov-fail-under=60
```

## Backlog

- Investigate failed `Upload Python Package` workflow from the `v1.0.0` release.
- Raise coverage target from 60% toward 75%.
- Add more typed models for Steam API responses.
- Consider optional release automation documentation.
