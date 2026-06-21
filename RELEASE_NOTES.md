# Steam Review Exporter Release Notes

## v2.0.1 (Architecture Remediation & Web-Readiness)

Dieses Release behebt primär kritische konzeptionelle Fehler und Flaschenhälse, die in der Version `v2.0.0` aufgetreten sind. Die Änderungen stellen sicher, dass die Architektur nicht nur für das CLI fehlerfrei und robust läuft, sondern auch sauber in externe Web- und Edge-Technologien integriert werden kann.

### 🛠️ Critical Bug Fixes & Hotfixes

- **API Retry Loop & Hangs:** Es wurde ein Problem behoben, bei dem das CLI endlos hängen bleiben konnte, wenn Rate-Limits (HTTP 429/500+) auftraten. Es greift nun ein hartes Limit (`MAX_RETRIES = 5`) mit sauberem Exponential Backoff.
- **SQLite DB Locking (Windows):** Ein schwerer Bug wurde behoben, bei dem offene SQLite-Datenbankverbindungen unter Windows Dateisystem-Sperren verursachten.
- **Run Isolation & Cache Context Mixing:** Das Cache-Verhalten wurde korrigiert, um Export-Vermischungen bei unterschiedlichen Filter-Läufen zu verhindern.
- **Infinite Loop Protection:** Der Paginierungs-Loop-Schutz wurde komplett überarbeitet. Cursors werden nun sicher über einen SHA256-Hash der Request-Parameter getrackt. So werden fehlerhafte Steam-Paginierungen sofort über einen `SteamCursorLoopError` abgebrochen.

### 🏗️ Konzeptionelle Architektur-Korrekturen

- **Dependency Inversion (Storage-Abstraktion):** Die harte Kopplung an SQLite war ein architektonischer Fehler für zustandslose Umgebungen. SQLite wurde hinter ein `ReviewStorageProtocol` abstrahiert. Zusätzlich wurden `MemoryStorage` und `NullStorage` für Edge/Web-Szenarien implementiert.
- **Asynchrones Streaming:** Statt riesige Datenmengen auf einmal im RAM zu sammeln, stellt der `SteamReviewScraper` jetzt `fetch_reviews_stream()` bereit. Dies ermöglicht echtes Chunking/Streaming an Frontends ohne Timeouts.
- **Leichtgewichtiger Core:** Schwere Abhängigkeiten (`polars` und `xlsxwriter`) wurden konsequenterweise in die `[project.optional-dependencies]` ausgelagert, um den Footprint in Microservices zu minimieren.

### 🛡️ Web-Kompatibilität & Error Handling

- **Exakte Exception-Hierarchie:** Statt Fehler stillschweigend mit `None` zu quittieren, werden nun saubere Errors geworfen (`SteamRateLimitError`, `SteamUnavailableError`, `SteamValidationError`). Diese können von Web-APIs direkt in HTTP-Statuscodes (z.B. 429, 503) gemappt werden.
- **Fail-Fast Rate Limiting:** Über das neue Flag `raise_on_rate_limit` im `SteamAPIClient` kann konfiguriert werden, ob der Scraper sich schlafen legt (CLI) oder sofort abbricht (Edge Function).

### 🧪 Quality Gates & Tests

- **Test-Coverage & Linter:** Alle Tests wurden repariert und massiv erweitert (insbesondere für Exception-Passthroughs und den asynchronen Stream). Die Test-Coverage stieg von 54% auf knapp 90%. Alle `ruff` und `mypy` Fehler wurden restlos eliminiert.

### 🔧 Upgrade Guide für Nutzer

Für bestehende Nutzer des **CLI-Tools** ändert sich nichts an der Bedienung.
Wer das Projekt **als Bibliothek** nutzen möchte, installiert nun zielgerichtet:
```bash
pip install steamreviews         # Für den schlanken, Web-Ready Core
pip install steamreviews[cli]    # Inklusive Polars und Excel-Support
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
