# Steam Review Exporter Release Notes

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
