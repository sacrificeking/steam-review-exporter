# Developer Guide

This guide explains how the project is structured and how to run the local quality checks.

## Project Architecture

The project is split into two main parts:

- `export_reviews.py`: command-line interface and user interaction.
- `steamreviews/`: reusable library code for downloading, processing, and exporting reviews.

```mermaid
graph TD
    User((User)) --> A[export_reviews.py]
    A -->|Config and validation| B[steamreviews package]

    subgraph "steamreviews"
        B --> C[models.py]
        B --> D[api.py]
        B --> S[scraper.py]
        B --> ST[storage.py]
        B --> E[export.py]
        B --> F[utils.py]
    end

    D -->|Async HTTP| SteamAPI[Steam API]
    S --> ST
    ST -->|SQLite cache| Data[data folder]
    E -->|Write| ExcelFile[Excel file]
```

## Key Files

| File | Purpose |
| :--- | :--- |
| `export_reviews.py` | CLI entry point. Supports interactive prompts and command-line arguments. |
| `steamreviews/models.py` | Pydantic validation for export configuration and Steam API payloads. |
| `steamreviews/api.py` | Async Steam API client with retries, rate limits, and typed errors. |
| `steamreviews/scraper.py` | Pagination orchestration and cursor-loop protection. |
| `steamreviews/storage.py` | SQLite, memory, and null storage backends. |
| `steamreviews/export.py` | Review filtering, URL generation, Excel safety, and Excel export. |
| `steamreviews/language_detection.py` | Steam language mapping and `lingua`-based review text detection. |
| `steamreviews/utils.py` | Logging setup. |
| `steamreviews/tests/` | Unit, export, CLI, and integration tests. |

## Setup

Install the project with development and CLI dependencies:

```bash
python -m pip install -e .[dev,cli]
```

## Fast Local Checks

Run these before committing:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy .
python -m pytest -m "not integration" --cov=steamreviews --cov-fail-under=75
```

The fast test suite does not call the live Steam API.

## Integration Tests

Integration tests are marked with `integration` because they call the live Steam API.
Run them explicitly when needed:

```bash
python -m pytest -m integration
```

These tests use temporary working directories and should not delete local project data.

## CLI Examples

Interactive mode:

```bash
steam-review-exporter
```

Scriptable mode:

```bash
steam-review-exporter --app-id 588650 --language english --filter recent --min-len 100 --cache-dir data --output-dir exports
```

Partial downloads return exit code `3` when an Excel file was still written from cached reviews.

CI tests the package on Python 3.11, 3.12, and 3.13. Dependency updates are managed via Renovate with grouped patch/minor PRs.