# Agent Instructions

These instructions are repository-local operating rules. Higher-priority host, system, developer, and user instructions still apply.

## 1. Session Bootstrap

For every non-trivial task:

1. Read `AGENTS.md`, `CODEX.md`, `INSTRUCTIONS.md`, `tasks/todo.md`, and `tasks/lessons.md`.
2. Run `git status -sb`.
3. Inspect the files directly relevant to the request.
4. State memory layer status in the working summary or final response.

For trivial one-command questions, answer directly without ceremony.

## 2. Planning Rule

Use explicit planning when a task has 3+ steps, changes architecture, touches CI/release behavior, or affects user-facing workflows.

Planning means:

1. Update `tasks/todo.md` with the current goal, assumptions, steps, and verification gates.
2. Keep the plan short enough to execute.
3. Ask for confirmation only when requirements are ambiguous or risk is high.
4. During execution, keep task status current.

## 3. Implementation Rule

1. Prefer existing project patterns.
2. Keep changes scoped to the request.
3. Use small helper functions only when they reduce real complexity or improve testability.
4. Preserve backward compatibility unless the user approved a breaking change.
5. Avoid unrelated refactors.
6. Do not commit generated artifacts, caches, local data, credentials, or exported `.xlsx` files.

## 4. Verification Rule

Run the narrowest sufficient checks, then broaden when risk increases.

Default fast checks:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy .
python -m pytest -m "not integration" --cov=steamreviews --cov-fail-under=60
```

Integration tests are opt-in:

```bash
python -m pytest -m integration
```

Only run integration tests when the task explicitly involves live Steam API behavior or the user asks for end-to-end validation.

## 5. Anti-Fragility Rule

Before finalizing non-trivial work, check:

1. Empty input.
2. Invalid input.
3. Network failure if applicable.
4. File permission or missing file behavior if applicable.
5. Backward compatibility with existing public APIs.
6. CI behavior.

## 6. Lessons Rule

After any user correction, failed assumption, repeated test failure, or missed requirement:

1. Add a dated entry to `tasks/lessons.md`.
2. Capture the exact pattern.
3. Add the new rule that prevents recurrence.

## 7. Release Rule

Before release work:

1. Ensure `master` is clean or understand all pending changes.
2. Run fast checks.
3. Update release notes.
4. Commit intentionally.
5. Tag intentionally.
6. Push branch and tag.
7. Verify GitHub release or CI status.

## 8. Final Response Rule

Every substantial final response should include:

- What changed.
- Verification performed.
- Commit/push status if relevant.
- Known limitations or follow-up risk.
- A direct answer to: would a staff engineer approve this?
