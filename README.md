# Steam Review Exporter

A command-line tool to download Steam reviews for any game and export them directly to Excel.

This project helps you to download Steam reviews for any game and export them directly to Excel.

## Features

-   **Download Reviews**: Fetch reviews for any Steam AppID.
-   **Excel Export**: Automatically saves reviews to a structured `.xlsx` file.
-   **Smart Language Filtering**: Uses Steam metadata plus `lingua` content analysis to ensure accurate language results (fixes common Steam API issues).
-   **Filtering**: Sort by "Helpful", "Funny", "Recent", or "Updated".
-   **Interactive Mode**: Simple step-by-step prompts to guide you through the process.
-   **Robust Validation**: Checks inputs automatically to prevent errors (powered by Pydantic).
-   **Beautiful Output**: Colored logging and progress bars (powered by Rich).
-   **Library Access**: Full access to the underlying `steamreviews` library for developers.

## Installation

### 1. Prerequisites
-   **Install Python**: Download and install [Python 3.11 or newer](https://www.python.org/downloads/).
    -   **Important**: During installation, check the box that says **"Add Python to PATH"**.

### 2. Download and Install
1.  **Download the Code**:
    Download this project (click "Code" > "Download ZIP") and extract it to a folder on your computer.

2.  **Open a Terminal**:
    -   Go to the folder where you extracted the files.
    -   Right-click in the empty space of the folder window and select "Open Terminal here" or "Open PowerShell window here".

3.  **Install Dependencies**:
    Run this command to install the CLI with Excel export support:
    ```bash
    python -m pip install .[cli]
    ```
    For library-only use without Excel export:
    ```bash
    python -m pip install .
    ```
    *(For Developers: See the [Developer Guide](DEVELOPER_GUIDE.md) for setup and testing instructions)*

## Usage

### Option 1: Interactive Mode
After installation, you can run the tool from anywhere in your terminal:

```bash
steam-review-exporter
```

### Option 2: Run directly (If "command not found")
If the command above doesn't work, you can always run the script directly from the project folder:

```bash
python export_reviews.py
```

Follow the on-screen prompts to:
1.  Enter the Steam App-ID (e.g., `588650` for Dead Cells).
    -   *Tip: You can find the AppID in the store URL: `store.steampowered.com/app/<AppID>/`*
2.  Choose a language (e.g., `english`, `german`, or `all`).
3.  Select a filter:
    -   **All**: Default, sorted by helpfulness.
    -   **Funny**: Sorted by "funny" votes.
    -   **Recent**: Sorted by creation date.
    -   **Updated**: Sorted by update date.
4.  **Optional**: Filter by review length.
    -   Enter a minimum character count (e.g., `100`).
    -   Enter a maximum character count (e.g., `500`) or press Enter for no limit.

The tool will download the reviews and save an Excel file...

### Option 2: Scriptable Command
You can also run the exporter without prompts:

```bash
steam-review-exporter --app-id 588650 --language english --filter recent --min-len 100 --max-len 500 --output-dir exports
```

Available options:

-   `--app-id`: Steam AppID.
-   `--language`: Steam language, e.g. `english`, `german`, or `all`.
-   `--filter`: One of `all`, `funny`, `recent`, or `updated`.
-   `--min-len`: Minimum review length in characters.
-   `--max-len`: Maximum review length in characters.
-   `--cache-dir`: Directory for the SQLite review cache. Defaults to `./data`.
-   `--output-dir`: Directory for the Excel export.
-   `--verbose`: Enable debug logging.

Exit codes:

-   `0`: Export completed successfully.
-   `1`: Export failed or no reviews were found.
-   `2`: Invalid CLI configuration.
-   `3`: Excel was written from a partial/incomplete Steam download.

---

### 3. Python Library (Advanced)
You can use the underlying `steamreviews` package in your own Python scripts.

> **Note**: The Steam API is rate-limited. Expect roughly 10 reviews per second.

Install the library:

```bash
python -m pip install .          # Core library (async API client + scraper)
python -m pip install .[cli]     # Adds Polars + Excel export helpers
```

#### Download reviews for one AppID
```python
import asyncio

from steamreviews import MemoryStorage, SteamReviewScraper

async def main() -> None:
    scraper = SteamReviewScraper(storage=MemoryStorage())
    request_params = {"json": "1", "num_per_page": "100", "language": "english"}
    await scraper.fetch_all_reviews(588650, request_params)
    reviews = list(scraper.storage.load_run_reviews(scraper.run_id, 588650))
    print(f"Downloaded {len(reviews)} reviews")

asyncio.run(main())
```

#### Stream reviews batch by batch
```python
import asyncio

from steamreviews import NullStorage, SteamReviewScraper

async def main() -> None:
    scraper = SteamReviewScraper(storage=NullStorage())
    request_params = {"json": "1", "num_per_page": "100", "filter": "recent"}
    async for batch in scraper.fetch_reviews_stream(588650, request_params):
        print(f"Received batch of {len(batch)} reviews")

asyncio.run(main())
```

#### Download, filter, and export to Excel
```python
import asyncio

from steamreviews.export import fetch_reviews, process_reviews, save_to_excel

async def main() -> None:
    result = await fetch_reviews(
        app_id=588650,
        language="english",
        filter_type="recent",
        min_len=100,
        cache_dir="data",
    )
    reviews = result.reviews
    if result.outcome.partial:
        print("Warning: export is based on a partial download")
    df = process_reviews(reviews, app_id=588650)
    save_to_excel(df, 588650, "Dead Cells", "english", filter_type="recent", min_len=100)

asyncio.run(main())
```

#### Advanced Steam API parameters
Pass Steam request parameters directly to the scraper:

```python
request_params = {
    "json": "1",
    "num_per_page": "100",
    "language": "english",
    "review_type": "positive",      # positive, negative, or all
    "purchase_type": "steam",       # steam or non_steam_purchase
    "filter": "recent",             # all, recent, updated
    "day_range": "28",
}
```

Reference: [Steam Partner Documentation](https://partner.steamgames.com/doc/store/localization#supported_languages)

## Troubleshooting

### "pip" is not recognized...
If you see an error saying `pip` or `python` is not recognized:
1.  Reinstall Python.
2.  Make sure to check the box **"Add Python to environment variables"** (or "PATH") at the start of the installation.
3.  Restart your computer.

### Permission Errors
If you get an error when saving the Excel file, make sure the file isn't currently open in Excel. Close it and try again.
