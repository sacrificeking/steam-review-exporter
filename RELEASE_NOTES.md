# Steam Review Exporter Release Notes

## v2.0.1 (Hotfix & Remediation)

This release addresses critical bugs, test failures, and architecture bottlenecks identified in the `v2.0.0` architectural overhaul. 

### Critical Bug Fixes
- **API Retry Loop & Hangs:** Fixed an issue where the CLI could hang indefinitely when encountering rate limits (HTTP 429/500+). Implemented a hard limit (`MAX_RETRIES = 5`) and exponential backoff.
- **SQLite DB Locking (Windows):** Fixed a severe bug where the SQLite database connections were leaked and left open on Windows, preventing downstream tools and file-system cleanup from functioning. Added `with sqlite3.connect` and `conn.close()` in `finally` blocks for transactional integrity.

### Architecture Improvements
- **Run Isolation & Cache Context Mixing:** The SQLite Cache now acts as a true database. Generated a unique `run_id` for every scraper execution. `export.py` now queries reviews linked *only* to the current `run_id`, preventing exports from pulling in reviews downloaded during previous disjoint filter runs.
- **SQLite Cursor Tracking:** Overhauled the cursor loop protection. Cursors are now tracked securely by a SHA256 hash of the `request_params` (`params_hash`). This allows the scraper to cache cursors for different filters simultaneously without erroneously aborting loops.

### Testing & QA (Fast-Gates)
- **100% Test Pass Rate:** Fixed all broken tests. Wrote new test files for `api.py`, `scraper.py`, `cache.py`, and `export.py`.
- **Coverage Increased:** Test coverage successfully raised from 54% to **89.27%** (Target: 75%).
- **Linting & Typing:** Brought the codebase back into full compliance with `ruff check` and `mypy` strict type-checking. All Pydantic model types correctly cast and validated.

---

## 2.0.0

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
- PyPI publishing still uses the conservative Twine credentials path with `PYPI_USERNAME` and `PYPI_PASSWORD` secrets.

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
