# Steam API Skill

Use this skill when modifying `steamreviews/api.py`, `steamreviews/scraper.py`, or behavior involving Steam API requests.

## Invariants

- Every network request must have a timeout.
- Live Steam API behavior must not be required for fast tests.
- Rate limits and temporary HTTP failures must be handled predictably.
- Cache writes must avoid corrupting existing data.
- API responses with `success != 1` must be treated as failures.
- Reviews without `recommendationid` must be skipped, not crash storage.

## Request Handling Checklist

1. Use HTTPS endpoints.
2. Include a versioned user agent from package metadata.
3. Set connect and read timeouts via `httpx.Timeout`.
4. Handle `httpx.RequestError`.
5. Handle invalid JSON.
6. Validate payloads with Pydantic models.
7. Treat 429, 500, 502, 503, and 504 as temporary failures.
8. Keep retries bounded by configured rate limits.
9. Reject `success != 1` responses before pagination continues.

## Storage Checklist

1. Use `Path`, not string concatenation, for file paths.
2. Support custom `data_dir` for tests and callers.
3. Use WAL mode for SQLite.
4. Skip reviews missing `recommendationid` with a warning.
5. Track cursors per request-parameter hash to prevent infinite loops.

## Test Strategy

- Mock `httpx` transports for timeout/header/error behavior.
- Use `tmp_path` or temporary directories for SQLite tests.
- Keep live API tests marked as `integration`.
- Use VCR cassettes for real response-shape validation.