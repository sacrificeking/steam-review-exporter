# Steam Review Exporter 1.0.0

First stable release of Steam Review Exporter.

## Highlights

- Added an interactive command-line workflow for downloading Steam reviews by AppID.
- Added Excel export with generated Steam review URLs.
- Added language filtering with Steam metadata and optional content verification.
- Added review length filtering.
- Added Pydantic-based input validation.
- Added rich console logging and progress indicators.
- Migrated packaging to `pyproject.toml`.
- Added Ruff, Mypy, Pytest, and Pytest coverage support for development checks.
- Added developer documentation and refreshed user documentation.

## User-Facing Features

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

## Developer Notes

- The project now installs from `pyproject.toml`.
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
python -m pytest --ignore=steamreviews/tests/test_integration.py
```

## Validation

The 1.0.0 release candidate was checked with:

- Ruff lint
- Ruff format check
- Mypy
- Pytest unit and model tests

## Known Limitations

- Integration tests call the live Steam API and should be run separately from the fast local test suite.
- Steam API requests are still network-dependent and may be affected by rate limits or temporary Steam service issues.
- The CLI is currently primarily interactive; scriptable command-line arguments are planned for a later release.
