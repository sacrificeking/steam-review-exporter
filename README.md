# Steam Review Exporter

A command-line tool to download Steam reviews for any game and export them directly to Excel.

This project helps you to download Steam reviews for any game and export them directly to Excel.

## Features

-   **Download Reviews**: Fetch reviews for any Steam AppID.
-   **Excel Export**: Automatically saves reviews to a structured `.xlsx` file.
-   **Smart Language Filtering**: Uses metadata and content analysis to ensure accurate language results (fixes common Steam API issues).
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
    Run this command to install the necessary libraries:
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
-   `--output-dir`: Directory for the Excel export.
-   `--verbose`: Enable debug logging.

---

### 2. Python Library (Advanced)
You can use the underlying `steamreviews` package in your own Python scripts, just like in the original project.

> **Note**: The Steam API is rate-limited. You should be able to download about 10 reviews per second.

#### Download reviews for one AppID
```python
import steamreviews

app_id = 588650 # Dead Cells
review_dict, query_count = steamreviews.download_reviews_for_app_id(app_id)
```

#### Process a batch of AppIDs
```python
import steamreviews

app_ids = [329070, 573170]
steamreviews.download_reviews_for_app_id_batch(app_ids)
```

#### Advanced Filtering
You can pass specific request parameters to filter reviews by language, sentiment, or time range.

**Example: Download recent positive reviews**
```python
import steamreviews

request_params = dict()
# Reference: https://partner.steamgames.com/doc/store/localization#supported_languages
request_params['language'] = 'english'
request_params['review_type'] = 'positive' # or 'negative', 'all'
request_params['purchase_type'] = 'steam' # or 'non_steam_purchase'

app_id = 588650
review_dict, query_count = steamreviews.download_reviews_for_app_id(
    app_id,
    chosen_request_params=request_params
)
```

**Example: Download reviews from the last 28 days**
```python
import steamreviews

request_params = dict()
request_params['filter'] = 'recent' # or 'updated', 'all' (helpful)
request_params['day_range'] = '28'

app_id = 588650
review_dict, query_count = steamreviews.download_reviews_for_app_id(
    app_id,
    chosen_request_params=request_params
)
```

## Troubleshooting

### "pip" is not recognized...
If you see an error saying `pip` or `python` is not recognized:
1.  Reinstall Python.
2.  Make sure to check the box **"Add Python to environment variables"** (or "PATH") at the start of the installation.
3.  Restart your computer.

### Permission Errors
If you get an error when saving the Excel file, make sure the file isn't currently open in Excel. Close it and try again.
