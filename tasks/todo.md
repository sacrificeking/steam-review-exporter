# Task Plan

Persistent task board for agent-assisted development.

## Current Status

- Repository baseline: `v1.0.0` released.
- Post-1.0 hardening commit pushed: request timeouts, test separation, CLI args, cache safety, export tests, and coverage gate.
- Agent memory setup is in place.
- Current objective: v1.0.1 GitHub release published; PyPI publishing is blocked until `PYPI_PASSWORD` is configured.

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
python -m pytest -m "not integration" --cov=steamreviews --cov-fail-under=75
```

## Active Task: Upload Python Package Workflow Failure

Status: investigated

Steps:

1. Inspect GitHub Actions state for the failed `v1.0.0` release workflow. Completed.
2. Read the publish workflow and packaging configuration. Completed.
3. Identify the root cause and whether it is workflow, packaging, secret, or environment related. Completed.
4. Document a focused fix recommendation without publishing remote changes. Completed.
5. Use the findings to inform the next refactoring plan. Completed.

Findings:

- Failed run: `Upload Python Package`, run `26641820335`, event `release`, tag `v1.0.0`, commit `41b9e7b`.
- Primary failure: `.github/workflows/python-publish.yml` runs `python setup.py sdist bdist_wheel`, but the repository uses `pyproject.toml` and has no `setup.py` at `v1.0.0`.
- Secondary blocker: `TWINE_USERNAME` and `TWINE_PASSWORD` were empty in the failed run, so publishing would likely fail after the build step unless PyPI credentials or trusted publishing are configured.
- Workflow uses `python-version: '3.x'`, which resolved to Python 3.14.5 in the run. The package declares `requires-python = ">=3.11"`, but the main CI only tests 3.11 and 3.12.

Recommended fix:

1. Replace legacy `setup.py` build with a PEP 517 build: install `build` and run `python -m build`.
2. Prefer PyPI trusted publishing with `pypa/gh-action-pypi-publish` and workflow `id-token: write`; otherwise configure a scoped PyPI API token and use Twine explicitly.
3. Pin release build Python to a tested version such as `3.12` until CI expands to newer versions.
4. Add a non-publishing package build check to the normal CI workflow so packaging breakage is caught before release creation.

## Active Task: Refactoring Plan

Status: drafted

Goal:

Reduce coupling between the interactive CLI, Steam API download/cache logic, review transformation, and release/package automation while preserving the current public CLI and library behavior.

Phase 1: Release and Packaging Safety

Status: completed

Decision:

- Use the quick conservative publishing path: keep Twine with `PYPI_USERNAME` and `PYPI_PASSWORD` secrets for now.
- Do not switch to PyPI trusted publishing in this phase.

Steps:

1. Update `.github/workflows/python-publish.yml` to build from `pyproject.toml`. Completed.
2. Add package build verification to `.github/workflows/python-package.yml`. Completed.
3. Pin release build Python to `3.12`. Completed.
4. Add `twine check` before publishing and in CI package verification. Completed.
5. Verify locally with `python -m build`, `twine check`, and the existing fast checks. Completed.

Verification:

- Package build passed with `pyproject-build` from the project virtual environment.
- `twine check dist/*` passed.
- `ruff check` passed.
- `ruff format --check` passed.
- `mypy` passed.
- `pytest -m "not integration" --cov=steamreviews --cov-fail-under=60` passed: 27 passed, 3 deselected, total coverage 74.80%.

Notes:

- Local `python -m build` is shadowed by an existing ignored `build/` directory, so local verification used the equivalent `pyproject-build` console entry point.
- Setuptools emitted a deprecation warning for the license classifier; keep this as later packaging cleanup.
- Pytest emitted a Windows cache warning for `.pytest_cache`; tests still passed.

Phase 2: CLI Boundary

Status: completed

Steps:

1. Move config creation and prompting out of `main()` into small testable functions. Completed.
2. Keep `parse_args()` and `ReviewExportConfig` as the stable input boundary. Completed.
3. Make non-interactive CLI execution return a meaningful process status instead of swallowing every exception. Completed.
4. Add tests for invalid CLI config, empty result, downloader failure, and export failure. Completed.

Verification:

- Targeted CLI tests passed: 8 passed.
- `ruff check` passed.
- `ruff format --check` passed.
- `mypy` passed.
- `pytest -m "not integration" --cov=steamreviews --cov-fail-under=60` passed: 31 passed, 3 deselected, total coverage 75.83%.

Notes:

- `main()` now returns a process-style status code and `__main__` exits with it.
- The package entry point can use the same return code through the console script wrapper.
- Interactive repeat behavior is preserved through `get_next_config()`.

Phase 3: Steam API Client Boundary

Status: completed

Steps:

1. Introduce typed request/response aliases or lightweight models for Steam review payloads. Completed.
2. Extract HTTP request execution from pagination/cache mutation so retries and response parsing are isolated. Completed.
3. Make cache path handling consistently `Path` based internally. Completed.
4. Preserve existing exported functions in `steamreviews.__init__` for backward compatibility. Completed.

Verification:

- Targeted download/unit tests passed: 13 passed.
- `ruff check` passed.
- `ruff format --check` passed.
- `mypy` passed.
- `pytest -m "not integration" --cov=steamreviews --cov-fail-under=60` passed: 35 passed, 3 deselected, total coverage 78.52%.

Notes:

- Added typed aliases and `SteamApiResponse` for the Steam response boundary.
- Added `execute_steam_api_request()` for transport behavior and `parse_steam_api_response()` for response validation.
- Kept `download_reviews_for_app_id_with_offset()` and package exports backward compatible.
- Public path helpers still return strings; internal cache path handling now uses `Path` through `get_data_dir_path()` and `get_output_path()`.

Phase 4: Export Pipeline Boundary

Status: completed

Steps:

1. Split `fetch_reviews()` into download orchestration, language filtering, length filtering, and review normalization. Completed.
2. Keep Excel sanitization and filename construction independent and fully unit-tested. Completed.
3. Make language detection injectable so tests do not depend on global `langdetect` behavior. Completed.
4. Add focused tests for `language="all"`, unknown Steam language, short reviews, and malformed author data. Completed.

Verification:

- Targeted export tests passed: 14 passed.
- `ruff check` passed.
- `ruff format --check` passed.
- `mypy` passed.
- `pytest -m "not integration" --cov=steamreviews --cov-fail-under=60` passed: 40 passed, 3 deselected, total coverage 79.30%.

Notes:

- `fetch_reviews()` now composes smaller helpers for request params, payload download, payload normalization, language filtering, and length filtering.
- Language detection is injectable in `filter_reviews_by_language()`.
- Export behavior and public function names remain backward compatible.

Phase 5: Verification Ratchet

Status: completed

Steps:

1. Run the standard fast gates after each phase. Completed.
2. Raise coverage only after refactoring behavior is pinned with tests. Completed.
3. Keep live Steam API integration tests opt-in. Completed.
4. Review `git diff` after every phase for accidental behavior or public API changes. Completed.

Verification:

- Coverage gate raised from 60 to 75 in CI, developer instructions, task gates, and testing skill.
- `pytest -m "not integration" --cov=steamreviews --cov-fail-under=75` passed: 40 passed, 3 deselected, total coverage 79.30%.
- `ruff check` passed.
- `ruff format --check` passed.
- `mypy` passed.
- Package build passed with `pyproject-build`.
- `twine check dist/*` passed.

Notes:

- Integration tests remain opt-in via the `integration` marker.
- Setuptools still emits a license-classifier deprecation warning during package build; keep as later packaging cleanup.

## Active Task: Critical Review Follow-Up

Status: in progress

Goal:

Address the highest-risk review findings in priority order after the completed refactoring phases.

Steps:

1. Make Excel export failures affect CLI success/failure status. Completed.
2. Add an installed CLI/console-script behavior check. Completed.
3. Continue splitting the downloader loop into smaller units. Completed.
4. Validate Steam API payload shapes more strictly. Completed.
5. Clean up packaging metadata and prepare next release notes/version. Completed.

Finding 1 Verification:

- `save_to_excel()` now returns `True` only when the DataFrame is written.
- `export_once()` now returns the actual Excel-write status.
- Added tests for empty export data, permission errors, and CLI failure when export writing returns `False`.
- `ruff check` passed.
- `ruff format --check` passed.
- `mypy` passed.
- `pytest -m "not integration" --cov=steamreviews --cov-fail-under=75` passed: 43 passed, 3 deselected, total coverage 80.31%.

Finding 2 Verification:

- Added checks that the installed `steam-review-exporter` console script entry point resolves to `export_reviews:main`.
- Added wrapper-semantics checks for successful exit code `0` and argparse failure code `2`.
- Targeted CLI tests passed: 12 passed.
- `ruff check` passed.
- `ruff format --check` passed.
- `mypy` passed.
- `pytest -m "not integration" --cov=steamreviews --cov-fail-under=75` passed: 46 passed, 3 deselected, total coverage 80.86%.

Finding 3 Verification:

- Extracted timestamp filter setup and application from the downloader loop.
- Extracted review ID collection, redundant-batch detection, and cache merge helpers.
- Added focused tests for timestamp filter selection, timestamp filtering, redundant batch detection, and merge behavior.
- Targeted download/unit tests passed: 17 passed.
- `ruff check` passed.
- `ruff format --check` passed.
- `mypy` passed.
- `pytest -m "not integration" --cov=steamreviews --cov-fail-under=75` passed: 50 passed, 3 deselected, total coverage 83.43%.

Finding 4 Verification:

- Added `parse_steam_api_payload()` to validate decoded Steam API payload shape before returning parsed data.
- Rejects non-object payloads and invalid `reviews`, `query_summary`, or `cursor` shapes with a controlled failure tuple.
- Preserves existing missing-`success` behavior when the payload shape is otherwise valid.
- Targeted download/unit tests passed: 22 passed.
- `ruff check` passed.
- `ruff format --check` passed.
- `mypy` passed.
- `pytest -m "not integration" --cov=steamreviews --cov-fail-under=75` passed: 55 passed, 3 deselected, total coverage 84.22%.

Finding 5 Verification:

- Selected next version `1.0.1` as a SemVer patch release for backward-compatible bug fixes, workflow hardening, and internal refactoring.
- Updated `pyproject.toml` to version `1.0.1`.
- Replaced deprecated license classifier metadata with `license = "MIT"`.
- Added release notes for `1.0.1`.
- Package build passed with `pyproject-build`; the previous license-classifier deprecation warning is gone.
- `twine check dist/steam_review_exporter-1.0.1*` passed.
- `ruff check` passed.
- `ruff format --check` passed.
- `mypy` passed.
- `pytest -m "not integration" --cov=steamreviews --cov-fail-under=75` passed: 55 passed, 3 deselected, total coverage 84.22%.

Release Steward Notes:

- Final local diff reviewed before commit.
- Commit `c7bd368` pushed to `master`.
- Annotated tag `v1.0.1` pushed.
- GitHub Release `v1.0.1` published: https://github.com/sacrificeking/steam-review-exporter/releases/tag/v1.0.1
- Master CI passed after publishing.
- PyPI publish workflow built and validated the package but failed at upload with `403 Forbidden` because PyPI credentials were missing.
- Repository secret `PYPI_USERNAME` is now configured as `__token__`; `PYPI_PASSWORD` still needs a scoped PyPI API token before the failed release workflow can be rerun.

## Active Task: Audit Iteration 2 Architecture Fixes

Status: completed

Goal:

Fix the urgent audit findings around HTTP connection pooling, SQLite generator resource lifetime, delayed filter logging, and honest export memory behavior while preserving CLI/library compatibility.

Steps:

1. Reuse one `httpx.AsyncClient` across scraper API requests through an async `SteamAPIClient` lifecycle. Completed.
2. Remove SQLite connection ownership from lazy review generators. Completed.
3. Move user-facing filter initialization logs out of delayed iterator execution. Completed.
4. Add explicit Excel row/RAM guardrails for very large exports. Completed.
5. Add focused regression tests for the fixed architecture risks. Completed.
6. Run fast verification and review the final diff. Completed.

Verification gates:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy .
python -m pytest -m "not integration" --cov=steamreviews --cov-fail-under=75
```

Verification:

- Targeted audit tests passed: 38 passed.
- `ruff check .` passed.
- `ruff format --check .` passed with escalated execution after the sandbox hit a Windows ACL error.
- `mypy .` passed.
- `pytest -m "not integration" --cov=steamreviews --cov-fail-under=75` passed: 47 passed, total coverage 90.29%.
- `git diff --check` passed with only line-ending normalization warnings.

## Active Task: KPMG-Style Audit Implementation (v2.0.1 Hardening)

Status: completed

Goal:

Ensure repository release-readiness through thread-safety hardening, CI/CD validation updates, logging fallbacks, async loop safety, and clean diagnostics.

Steps:

1. Add thread-safety lock for `langdetect` in `steamreviews/export.py`. Completed.
2. Update `.github/workflows/python-package.yml` to install CLI extras in CI. Completed.
3. Handle missing `rich` gracefully in `steamreviews/utils.py`. Completed.
4. Run blocking sync `get_game_name` in a worker thread in `export_reviews.py`. Completed.
5. Provide explicit `ImportError` installation recommendations in `steamreviews/export.py`. Completed.
6. Verify and reformat code to pass all ruff, mypy, and pytest gates. Completed.

Verification:
- Ruff check and format pass.
- Mypy check passes.
- Pytest suite passes: 48 passed, coverage 89.97%.

## Active Task: KPMG Audit Findings Remediation (AUD-06 to AUD-10)

Status: completed

Goal:
Address the findings (AUD-06, AUD-07, AUD-08, AUD-09, and AUD-10) from the KPMG-style code audit.

Steps:
1. Define and export `SteamNotFoundError` to classify HTTP 404 responses differently from general 5xx unavailability. (Completed)
2. Enable WAL (Write-Ahead Logging) mode on database initialization to reduce concurrent locking risks. (Completed)
3. Harden Pydantic schema validation for `SteamReviewAuthor` to make secondary attributes optional and prevent crashes on missing API fields. (Completed)
4. Parameterize memory warning thresholds and maximum Excel export row limits with environment variables. (Completed)
5. Add unit tests for HTTP error handling, SQLite WAL status, schema resilience, and dynamic limits parameterization. (Completed)

Verification:
- Ruff check and format pass.
- Mypy check passes.
- Pytest suite passes: 52 passed, coverage 90.50%.

## Backlog

- Add more typed models for Steam API responses.
- Consider optional release automation documentation.

