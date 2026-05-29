# Task Plan

Persistent task board for agent-assisted development.

## Current Status

- Repository baseline: `v1.0.0` released.
- Post-1.0 hardening commit pushed: request timeouts, test separation, CLI args, cache safety, export tests, and 60% coverage gate.
- Agent memory setup is in place.
- Current objective: detailed dead-end and code-error review with fixes.

## Active Task: Agent Memory Setup

Status: completed

Steps:

1. Create root context files: `AGENTS.md`, `CODEX.md`, `INSTRUCTIONS.md`.
2. Create durable task memory: `tasks/todo.md`, `tasks/lessons.md`.
3. Create atomic skill manuals in `skills/`.
4. Verify repository checks still pass.
5. Review diff and commit/push when complete.

## Active Task: Release Governance Rules

Status: completed

Steps:

1. Encode SemVer release policy in `INSTRUCTIONS.md`.
2. Encode no-push-without-approval boundary in `CODEX.md`.
3. Update `skills/release/SKILL.md` with versioning and publishing gates.
4. Capture the user correction in `tasks/lessons.md`.
5. Verify checks locally.
6. Commit locally only; do not push without explicit approval.

## Active Task: Dead-End And Code Error Review

Status: completed

Steps:

1. Run baseline verification and stricter static checks.
2. Inspect all Python source, tests, packaging, and workflows for dead ends and likely bugs.
3. Fix confirmed issues with minimal scoped changes.
4. Add or adjust tests for every behavior fix.
5. Re-run fast verification and review final diff.
6. Do not push without explicit approval.

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
