# CLI And Export Skill

Use this skill when modifying `export_reviews.py`, `steamreviews/export.py`, or user-facing Excel output.

## CLI Principles

- Interactive mode must remain beginner-friendly.
- Scriptable mode must support automation.
- CLI arguments and interactive prompts must both flow through `ReviewExportConfig`.
- Invalid CLI combinations should fail early with clear messages.
- `--cache-dir` stores the SQLite review cache; `--output-dir` stores only Excel exports.
- Exit code `3` means an Excel file was written from a partial Steam download.

## Export Principles

- Exported rows should include `review_url` first when available.
- Review text must be protected from Excel formula injection.
- Do not mutate caller-provided review dictionaries unless explicitly intended.
- File names must be deterministic and safe for common filesystems.
- `output_dir` should create missing directories.
- `fetch_reviews()` returns `FetchReviewsResult` with filtered reviews and `FetchOutcome` metadata.

## Excel Injection Prefixes

Treat these prefixes as risky:

```text
=-@
tab
carriage return
```

Prefix risky cell text with an apostrophe before writing to Excel.

## Test Strategy

- Language filtering uses `lingua` via `steamreviews/language_detection.py`; inject custom detectors in tests.
- Mock downloads for language and length filtering.
- Mock `DataFrame.to_excel` for filename/output directory tests.
- Test both interactive helpers and CLI argument parsing where possible.
- Test partial-download exit code `3` and separate cache/output directories.