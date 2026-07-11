# Steam Review Exporter Release Notes

## v2.0.3

This release improves stability, error handling, and CLI behavior. Day-to-day CLI usage stays largely the same; developers using the Python library directly should read the notes under **Library users** below.

### 🛠️ Bug fixes & hardening

- **Reviews without `recommendationid`:** The SQLite cache skips reviews without a valid `recommendationid` instead of crashing with `KeyError`.
- **Pydantic `recommendationid`:** Integer values from the Steam API are reliably coerced to `str`.
- **Steam API `success` flag:** The scraper treats `success != 1` as a failure and stops pagination loops cleanly via `SteamCursorLoopError`.
- **Dynamic User-Agent:** The HTTP client sends a versioned User-Agent string from package metadata.
- **Excel injection protection:** `sanitize_excel_text` blocks tab characters and formula injection (`=`, `+`, `-`, `@`) in exported cells.
- **Partial downloads:** Interrupted Steam downloads still process cached reviews; the CLI reports this state with exit code `3`.
- **Separate directories:** `--cache-dir` controls the SQLite cache; `--output-dir` controls only the Excel export (the library previously tied both to `output_dir`).

### 📦 Dependencies & tooling

- **Language detection:** Replaced `langdetect` with `lingua-language-detector` (`steamreviews/language_detection.py`); the thread lock is no longer needed.
- **Dependency pinning:** Added upper version bounds for runtime and dev dependencies in `pyproject.toml`.
- **Renovate:** Added schedule, grouping, and automerge for patch updates in `renovate.json`.
- **CI:** Added Python **3.13** to the test matrix; added a `pip-audit` step for known CVEs.

### 📚 Documentation

- README and Developer Guide document `--cache-dir`, exit codes (`0`–`3`), and the updated library API with `FetchReviewsResult`.
- Updated skills (`cli-export`, `steam-api`) to match the new behavior.

### ⚠️ Library users

- `fetch_reviews()` now returns `FetchReviewsResult` with `.reviews` and `.outcome` instead of a direct iterable.
- The library parameter `output_dir` has been renamed to `cache_dir`.

### 🧪 Tests

- 21 new or extended tests (including partial-download exit code, language detection, scraper error paths, and cache/output directory separation).
- Test coverage is **94%** with **74** passing tests (excluding integration).

---

## v2.0.2

This release fixes bugs and hardens database stability, Pydantic models, and HTTP error classification.

### 🛠️ Bug fixes & hardening

- **HTTP error classification:** Introduced `SteamNotFoundError`. The client now distinguishes a genuinely missing App ID (HTTP 404) from general temporary server errors (5xx) instead of treating everything as service unavailability.
- **SQLite concurrency & WAL mode:** SQLite is now initialized in Write-Ahead Logging mode by default (`PRAGMA journal_mode=WAL;`). This improves parallel read/write throughput and reduces `database is locked` errors in multi-threaded scenarios.
- **Pydantic model resilience:** Hardened `SteamReviewAuthor` by declaring all secondary metadata attributes as optional (`int | None = None`). This prevents validation crashes when Valve removes or changes fields in the API payload without notice.
- **Configurable export thresholds:** `EXPORT_MEMORY_WARNING_ROWS` and `MAX_EXCEL_DATA_ROWS` can now be set via the `STEAM_EXPORT_WARN_ROWS` and `STEAM_EXPORT_MAX_ROWS` environment variables.
- **Database schema migration:** Automatic migration of outdated SQLite table structures. If the `params_hash` column is missing from the `cursors` table (e.g. after upgrading from 1.x), the table is reset and recreated automatically.

### 📦 Dependencies & tooling

- Updated all locked dependencies in `uv.lock` (including `polars v1.42.0`, `ruff v0.15.20`, `mypy v2.1.0`, and `rich v15.0.0`).
- Fixed new linter warnings surfaced by the Ruff upgrade.

### 🧪 Tests

- Added unit tests for HTTP error codes (404/400), WAL mode activation, optional Pydantic fields, environment variable overrides, and automatic DB schema migration. Test coverage is now **90.73%** with 53 passing tests.

---

## v2.0.1 (Architecture Remediation & Web-Readiness)

This release addresses critical conceptual issues and bottlenecks introduced in `v2.0.0`. The changes ensure the architecture runs reliably for the CLI and integrates cleanly into external web and edge environments.

### 🛠️ Critical bug fixes & hotfixes

- **API retry loop & hangs:** Fixed a case where the CLI could hang indefinitely on rate limits (HTTP 429/500+). A hard limit (`MAX_RETRIES = 5`) with exponential backoff now applies.
- **SQLite DB locking (Windows):** Fixed a severe bug where open SQLite connections caused filesystem locks on Windows.
- **Run isolation & cache context mixing:** Corrected cache behavior to prevent export mixing across different filter runs.
- **Infinite loop protection:** Reworked pagination loop protection. Cursors are now tracked via a SHA256 hash of request parameters, so faulty Steam pagination is stopped immediately via `SteamCursorLoopError`.

### 🏗️ Architectural corrections

- **Dependency inversion (storage abstraction):** Hard coupling to SQLite was an architectural problem for stateless environments. SQLite is now behind a `ReviewStorageProtocol`, with `MemoryStorage` and `NullStorage` added for edge/web scenarios.
- **Async streaming:** Instead of collecting large datasets in RAM, `SteamReviewScraper` now exposes `fetch_reviews_stream()` for true chunking/streaming to frontends without timeouts.
- **Lightweight core:** Heavy dependencies (`polars` and `xlsxwriter`) were moved to `[project.optional-dependencies]` to reduce the footprint in microservices.

### 🛡️ Web compatibility & error handling

- **Explicit exception hierarchy:** Instead of silently returning `None`, the client now raises clear errors (`SteamRateLimitError`, `SteamUnavailableError`, `SteamValidationError`) that web APIs can map directly to HTTP status codes (e.g. 429, 503).
- **Fail-fast rate limiting:** The new `raise_on_rate_limit` flag on `SteamAPIClient` lets callers choose between sleeping on rate limits (CLI) or failing immediately (edge functions).

### 🧪 Quality gates & tests

- **Test coverage & linting:** Repaired and significantly expanded tests (especially exception passthrough and async streaming). Coverage rose from 54% to nearly 90%. All `ruff` and `mypy` issues were resolved.

### 🔧 Upgrade guide

Nothing changes for existing **CLI** users.

Library users should install explicitly:

```bash
pip install steamreviews         # Lean, web-ready core
pip install steamreviews[cli]    # Includes Polars and Excel support
```



---

## v2.0.0

Massive "State of the Art" architectural rewrite to maximize performance, reliability, and modern web-readiness.

### Highlights

- **SQLite Database Caching**: Replaced monolithic JSON file caching with a high-performance SQLite database (`steam_reviews.db`). Eliminates massive RAM usage spikes and ensures crash-proof incremental saving.
- **Asynchronous Networking**: Replaced synchronous `requests` with asynchronous `httpx` and `asyncio`. Internal API is now non-blocking and ready for modern web framework integration (FastAPI, Next.js).
- **Polars Data Processing**: Replaced `pandas` with `polars` (Rust-based) for lightning-fast memory-efficient data processing and Excel exporting.
- **Infinite Loop Protection**: Added strict database-level cursor tracking to definitively prevent infinite API pagination loops.
- **Enhanced Security**: Hardened CSV/Formula injection prevention during Excel export.
- **Strict Linting & Validation**: Added strict `Pydantic` validation models for all incoming Steam API payloads.

### Breaking Changes

- Removed `steamreviews.download_reviews` module completely. The internal library API was heavily refactored into `steamreviews.api`, `steamreviews.scraper`, and `steamreviews.cache`.
- Export module functions and CLI logic now rely on `async`/`await`.
- Development dependencies now include `pytest-asyncio` instead of `types-requests`.


## 1.0.1

Patch release focused on release reliability, CLI exit correctness, export safety, and internal hardening.

### Fixes

- Fixed the Python package publish workflow to build from `pyproject.toml` instead of the removed `setup.py`.
- Fixed CLI success reporting so Excel export failures now produce a failing process status.
- Fixed release build drift by pinning the publish workflow to Python 3.12.
- Added package build and `twine check` validation to CI before release publishing.

### Hardening

- Split CLI execution into smaller testable functions while preserving the existing command interface.
- Added installed console-script entry point checks for `steam-review-exporter`.
- Split Steam API HTTP execution and response parsing into isolated helpers.
- Added stricter Steam API payload shape validation for decoded responses.
- Split export review fetching into request, payload normalization, language filtering, and length filtering steps.
- Kept live Steam API integration tests opt-in.
- Raised the fast coverage gate from 60% to 75%.

### Validation

The 1.0.1 release candidate was checked with:

- Ruff lint
- Ruff format check
- Mypy
- Pytest non-integration suite with coverage gate 75%
- Package build from `pyproject.toml`
- Twine package metadata check

### Known Limitations

- Integration tests still call the live Steam API and should be run separately.
- Steam API requests remain network-dependent and may be affected by rate limits or temporary Steam service issues.

## 1.0.0

First stable release of Steam Review Exporter.

### Highlights

- Added an interactive command-line workflow for downloading Steam reviews by AppID.
- Added Excel export with generated Steam review URLs.
- Added language filtering with Steam metadata and optional content verification.
- Added review length filtering.
- Added Pydantic-based input validation.
- Added rich console logging and progress indicators.
- Migrated packaging to `pyproject.toml`.
- Added Ruff, Mypy, Pytest, and Pytest coverage support for development checks.
- Added developer documentation and refreshed user documentation.

### User-Facing Features

- Download reviews for any Steam game by entering its AppID.
- Select review language such as `english`, `german`, or `all`.
- Select Steam review sorting/filter mode:
  - all
  - funny
  - recent
  - updated
- Optionally filter reviews by minimum and maximum text length.
- Export results to `.xlsx` files with a predictable filename format.
- Add a direct Steam community review URL to each exported review row.
- Protect exported review text against basic Excel formula injection.

### Developer Notes

- The project installs from `pyproject.toml`.
- The package exposes the underlying `steamreviews` library API.
- Development dependencies are available through:

```bash
python -m pip install -e .[dev]
```

- Recommended local checks:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy .
python -m pytest -m "not integration" --cov=steamreviews --cov-fail-under=75
```

### Validation

The 1.0.0 release candidate was checked with:

- Ruff lint
- Ruff format check
- Mypy
- Pytest unit and model tests

### Known Limitations

- Integration tests call the live Steam API and should be run separately from the fast local test suite.
- Steam API requests are still network-dependent and may be affected by rate limits or temporary Steam service issues.
