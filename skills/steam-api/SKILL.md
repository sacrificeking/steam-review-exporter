# Steam API Skill

Use this skill when modifying `steamreviews/download_reviews.py` or behavior involving Steam API requests.

## Invariants

- Every network request must have a timeout.
- Live Steam API behavior must not be required for fast tests.
- Rate limits and temporary HTTP failures must be handled predictably.
- Cache writes must avoid corrupting existing data.
- Existing public functions should remain backward compatible unless explicitly approved.

## Request Handling Checklist

1. Use HTTPS endpoints.
2. Include a user agent.
3. Set connect and read timeouts.
4. Handle `requests.exceptions.RequestException`.
5. Handle invalid JSON.
6. Treat 429, 500, 502, 503, and 504 as temporary failures.
7. Keep retries bounded by configured rate limits.

## Cache Checklist

1. Use `Path`, not string concatenation, for file paths.
2. Support custom `data_dir` for tests and callers.
3. Use UTF-8 for JSON reads/writes.
4. Write via temporary file and replace atomically.
5. Treat invalid cached JSON as recoverable with logging.

## Test Strategy

- Mock `requests.get` for timeout/header/error behavior.
- Use `tmp_path` or temporary directories for cache tests.
- Keep live API tests marked as `integration`.
