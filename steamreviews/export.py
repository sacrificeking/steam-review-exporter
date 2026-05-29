import steamreviews
import pandas as pd
import requests
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, cast
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

EXCEL_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

# Minimal mapping of Steam language names to ISO 639-1 codes
STEAM_LANG_TO_ISO = {
    "english": "en",
    "german": "de",
    "french": "fr",
    "spanish": "es",
    "italian": "it",
    "russian": "ru",
    "schinese": "zh-cn",
    "tchinese": "zh-tw",
    "japanese": "ja",
    "koreana": "ko",
    "portuguese": "pt",
    "brazilian": "pt",
}


def sanitize_filename_part(text: str) -> str:
    """
    Sanitizes a string to be safe for use in a filename.
    Allows alphanumeric characters, underscores, hyphens, and spaces.
    """
    # Replace non-alphanumeric/non-hyphen/non-underscore/non-space with empty string
    sanitized = re.sub(r"[^\w\-\s]", "", text)
    return sanitized.strip() or "unknown"


def sanitize_excel_text(text: str) -> str:
    """Prefixes potentially executable Excel cell text with an apostrophe."""
    if text.startswith(EXCEL_FORMULA_PREFIXES):
        return "'" + text
    return text


def build_output_filename(
    game_name: str,
    language: str,
    filter_type: str = "all",
    min_len: int = 0,
    max_len: Optional[int] = None,
) -> str:
    """Builds the Excel export filename."""
    safe_game_name = sanitize_filename_part(game_name)

    lang_iso = STEAM_LANG_TO_ISO.get(language, language).upper()
    if language == "all":
        lang_iso = "ALL"

    details = [filter_type if filter_type != "all" else "full"]
    if min_len > 0 or max_len is not None:
        upper_bound = str(max_len) if max_len is not None else "max"
        details.append(f"len-{min_len}-{upper_bound}")

    return f"{safe_game_name} {lang_iso} - Reviews {' '.join(details)}.xlsx"


def fetch_reviews(
    app_id: int, language: str, filter_type: str = "all", min_len: int = 0, max_len: Optional[int] = None
) -> List[Dict]:
    """
    Downloads reviews using the steamreviews library.

    Applies a two-stage language filter:
    1. Metadata: requests reviews with the specific language tag from Steam.
    2. Content: analyzes the actual review text using 'langdetect'
       to remove false positives (e.g., English reviews tagged as German).
    """
    request_params = {}
    if language and language != "all":
        request_params["language"] = language

    if filter_type and filter_type != "all":
        request_params["filter"] = filter_type

    try:
        # steamreviews usually returns (review_dict, query_count)
        # We need to trust it returns a dict-like structure.
        review_data: Dict = steamreviews.download_reviews_for_app_id(app_id, chosen_request_params=request_params)[0]
    except requests.exceptions.RequestException as e:
        logger.error(f"Network Error: Could not connect to Steam. Details: {e}")
        return []
    except Exception as e:
        logger.error(f"Error downloading reviews: {e}")
        return []

    reviews = review_data.get("reviews", [])
    if isinstance(reviews, dict):
        reviews = list(reviews.values())

    if language and language != "all":
        # API language codes are lowercase (e.g. 'english', 'schinese')
        target_lang = language.lower()

        # 1. Metadata Filter: Keep only reviews tagged with the requested language
        reviews = [r for r in reviews if r.get("language") == target_lang]

        # 2. Content Filter: Use langdetect to verify the text content
        target_iso = STEAM_LANG_TO_ISO.get(target_lang)

        if target_iso:
            logger.info(f"Applying content analysis for language '{target_lang}' (ISO: {target_iso})...")
            filtered_reviews = []
            removed_count = 0

            for r in reviews:
                text = r.get("review", "")
                # Skip detection for very short texts (unreliable)
                if len(text) < 10:
                    filtered_reviews.append(r)
                    continue

                try:
                    detected = detect(text)
                    # Keep if it matches target OR if we are unsure (safe default)
                    # We only drop if it STRONGLY matched another language?
                    # Actually, simple equality check is usually enough if langdetect is robust.
                    # But 'en' often detects 'de' words mixed in.
                    # Let's be strict: if detected is NOT target_iso, drop it.
                    if detected == target_iso:
                        filtered_reviews.append(r)
                    else:
                        # Optional: Add a whitelist for common mix-ups if needed.
                        # For now, strict filtering.
                        removed_count += 1
                except LangDetectException:
                    # Detection failed (e.g. no features), keep it to be safe
                    filtered_reviews.append(r)

            logger.info(f"Content Filter: Removed {removed_count} reviews that did not match '{target_iso}'.")
            reviews = filtered_reviews

    # 3. Length Filter
    if min_len > 0 or max_len is not None:
        initial_count = len(reviews)
        filtered_reviews = []
        for r in reviews:
            text_len = len(r.get("review", ""))

            # Check minimum length
            if text_len < min_len:
                continue

            # Check maximum length
            if max_len is not None and text_len > max_len:
                continue

            filtered_reviews.append(r)

        removed_len = initial_count - len(filtered_reviews)
        logger.info(
            f"Length Filter: Removed {removed_len} reviews outside length range "
            f"[{min_len}, {max_len if max_len is not None else 'Inf'}]."
        )
        reviews = filtered_reviews

    return cast(List[Dict], reviews)


def process_reviews(reviews: List[Dict], app_id: int) -> pd.DataFrame:
    """
    Processes reviews: generates URLs and sanitizes input to prevent Excel injection.
    Optimized to run in pure Python before DataFrame creation.
    """
    processed_data = []

    for raw_review in reviews:
        review = dict(raw_review)

        # 1. URL Generation
        author = review.get("author", {})
        steam_id = author.get("steamid")
        review_url = f"https://steamcommunity.com/profiles/{steam_id}/recommended/{app_id}/" if steam_id else ""

        # 2. Excel Injection Protection (Sanitize 'review' text)
        review_text = review.get("review", "")
        if isinstance(review_text, str):
            review["review"] = sanitize_excel_text(review_text)

        # 3. Add URL to the record
        review["review_url"] = review_url
        processed_data.append(review)

    df = pd.DataFrame(processed_data)

    # Reorder columns to ensure review_url is first if data exists
    if not df.empty and "review_url" in df.columns:
        cols = ["review_url"] + [c for c in df.columns if c != "review_url"]
        df = df[cols]

    return df


def save_to_excel(
    df: pd.DataFrame,
    app_id: int,
    game_name: str,
    language: str,
    filter_type: str = "all",
    min_len: int = 0,
    max_len: Optional[int] = None,
    output_dir: Optional[Union[str, Path]] = None,
) -> None:
    """Saves the DataFrame to an Excel file with format: {GameName} {Lang} - Reviews {Details}.xlsx"""
    if df.empty:
        logger.warning("No valid review data available to save.")
        return

    filename = build_output_filename(game_name, language, filter_type, min_len, max_len)
    output_path = Path(filename)
    if output_dir is not None:
        output_path = Path(output_dir) / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df.to_excel(str(output_path), index=False)
        logger.info(f"Reviews successfully saved to: {output_path}")
    except PermissionError:
        logger.error(f"Error: Permission denied. The file '{output_path}' seems to be open in Excel.")
        logger.error("Please close the file and try again.")
    except Exception as e:
        logger.error(f"Error saving file: {e}")
