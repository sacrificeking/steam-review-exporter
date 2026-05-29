# Testing Skill

Use this skill when changing Python code, tests, CI, packaging, or behavior that affects users.

## Purpose

Keep the fast feedback loop deterministic and network-free by default.

## Fast Verification

Run:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy .
python -m pytest -m "not integration" --cov=steamreviews --cov-fail-under=60
```

In this Windows workspace, use the virtualenv path when needed:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not integration"
```

## Integration Verification

Run only when requested or when live Steam API behavior is the task:

```bash
python -m pytest -m integration
```

## Failure Handling

1. Read the first failing assertion or traceback.
2. Identify whether failure is code, test, environment, or network.
3. Fix root cause, not symptoms.
4. Re-run the smallest failing command.
5. Re-run the full fast verification before finalizing.

## Done Criteria

- Fast checks pass.
- Integration tests remain opt-in.
- Coverage does not drop below configured threshold.
- Warnings are documented if they are environment-only and harmless.
