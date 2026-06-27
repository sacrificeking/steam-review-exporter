import logging
import os
import re
import threading
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

try:
    import polars as pl
except ImportError:
    pl = None  # type: ignore

if TYPE_CHECKING:
    import polars as _pl

from langdetect import LangDetectException, detect

from steamreviews.scraper import SteamReviewScraper

logger = logging.getLogger(__name__)

_langdetect_lock = threading.Lock()

EXCEL_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
MAX_EXCEL_DATA_ROWS = int(os.getenv("STEAM_EXPORT_MAX_ROWS", 1_048_575))
EXPORT_MEMORY_WARNING_ROWS = int(os.getenv("STEAM_EXPORT_WARN_ROWS", 250_000))
Review = dict[str, Any]
LanguageDetector = Callable[[str], str]

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
    sanitized = re.sub(r"[^\w\-\s]", "", text)
    return sanitized.strip() or "unknown"


def sanitize_excel_text(text: str) -> str:
    """Prefixes potentially executable Excel cell text with an apostrophe to prevent CSV/Formula injection."""
    stripped = text.lstrip()
    if stripped.startswith(EXCEL_FORMULA_PREFIXES):
        return "'" + text
    return text


def build_output_filename(
    game_name: str,
    language: str,
    filter_type: str = "all",
    min_len: int = 0,
    max_len: int | None = None,
) -> str:
    safe_game_name = sanitize_filename_part(game_name)

    lang_iso = STEAM_LANG_TO_ISO.get(language, language).upper()
    if language == "all":
        lang_iso = "ALL"

    details = [filter_type if filter_type != "all" else "full"]
    if min_len > 0 or max_len is not None:
        upper_bound = str(max_len) if max_len is not None else "max"
        details.append(f"len-{min_len}-{upper_bound}")

    return f"{safe_game_name} {lang_iso} - Reviews {' '.join(details)}.xlsx"


def build_review_request_params(language: str, filter_type: str = "all") -> dict[str, str]:
    request_params = {"json": "1", "num_per_page": "100"}
    if language and language != "all":
        request_params["language"] = language
    if filter_type:
        request_params["filter"] = filter_type
    return request_params


def filter_reviews_by_language(
    reviews: Iterable[Review],
    language: str,
    detector: LanguageDetector | None = None,
) -> Iterable[Review]:
    if not language or language == "all":
        return reviews

    target_lang = language.lower()
    target_iso = STEAM_LANG_TO_ISO.get(target_lang)
    detector = detector or detect

    if target_iso is None:
        return _filter_reviews_by_steam_language(reviews, target_lang)

    logger.info(f"Applying content analysis for language '{target_lang}' (ISO: {target_iso})...")
    return _filter_reviews_by_detected_language(reviews, target_lang, target_iso, detector)


def _filter_reviews_by_steam_language(reviews: Iterable[Review], target_lang: str) -> Iterable[Review]:
    for review in reviews:
        if review.get("language") == target_lang:
            yield review


def _filter_reviews_by_detected_language(
    reviews: Iterable[Review],
    target_lang: str,
    target_iso: str,
    detector: LanguageDetector,
) -> Iterable[Review]:
    removed_count = 0

    for review in reviews:
        if review.get("language") != target_lang:
            continue

        text = review.get("review", "")
        if not isinstance(text, str):
            text = ""

        if len(text) < 10:
            yield review
            continue

        try:
            # langdetect.detect is not thread-safe, so serialize calls to default detector
            if detector is detect:
                with _langdetect_lock:
                    detected_lang = detector(text)
            else:
                detected_lang = detector(text)

            if detected_lang == target_iso:
                yield review
            else:
                removed_count += 1
        except LangDetectException:
            yield review

    logger.info(f"Content Filter: Removed {removed_count} reviews that did not match '{target_iso}'.")


def filter_reviews_by_length(
    reviews: Iterable[Review], min_len: int = 0, max_len: int | None = None
) -> Iterable[Review]:
    if min_len <= 0 and max_len is None:
        return reviews

    logger.info(f"Applying length filter: min={min_len}, max={max_len if max_len is not None else 'No Limit'}.")
    return _filter_reviews_by_length(reviews, min_len, max_len)


def _filter_reviews_by_length(
    reviews: Iterable[Review], min_len: int = 0, max_len: int | None = None
) -> Iterable[Review]:
    removed_count = 0
    for review in reviews:
        review_text = review.get("review", "")
        text_len = len(review_text) if isinstance(review_text, str) else 0

        if text_len < min_len:
            removed_count += 1
            continue
        if max_len is not None and text_len > max_len:
            removed_count += 1
            continue

        yield review

    logger.info(
        f"Length Filter: Removed {removed_count} reviews outside length range "
        f"[{min_len}, {max_len if max_len is not None else 'Inf'}]."
    )


async def fetch_reviews(
    app_id: int,
    language: str,
    filter_type: str = "all",
    min_len: int = 0,
    max_len: int | None = None,
    output_dir: str | None = None,
) -> Iterable[dict[str, Any]]:
    from steamreviews.storage import SQLiteStorage

    storage = SQLiteStorage(data_dir=output_dir if output_dir else "data")
    scraper = SteamReviewScraper(storage=storage)
    request_params = build_review_request_params(language, filter_type)

    success = await scraper.fetch_all_reviews(app_id, request_params)
    if not success:
        logger.error("Fetch reviews encountered an error.")
        # We can still process what we have in cache

    reviews = scraper.storage.load_run_reviews(scraper.run_id, app_id)
    reviews_filtered_lang = filter_reviews_by_language(reviews, language)
    return filter_reviews_by_length(reviews_filtered_lang, min_len, max_len)


def _normalize_review_for_export(raw_review: dict[str, Any], app_id: int) -> Review:
    review = dict(raw_review)

    author = review.get("author") or {}
    if not isinstance(author, dict):
        author = {}
    steam_id = author.get("steamid")
    review_url = f"https://steamcommunity.com/profiles/{steam_id}/recommended/{app_id}/" if steam_id else ""

    review_text = review.get("review", "")
    if isinstance(review_text, str):
        review["review"] = sanitize_excel_text(review_text)

    if "author" in review:
        for k, v in author.items():
            review[f"author_{k}"] = v
        del review["author"]

    review["review_url"] = review_url
    return review


def _materialize_export_rows(reviews: Iterable[dict[str, Any]], app_id: int) -> list[Review]:
    rows: list[Review] = []
    for row_number, raw_review in enumerate(reviews, start=1):
        if row_number > MAX_EXCEL_DATA_ROWS:
            raise ValueError(
                "Excel export supports at most "
                f"{MAX_EXCEL_DATA_ROWS:,} data rows per sheet. "
                "Use stricter Steam filters or split the export into smaller runs."
            )
        if row_number == EXPORT_MEMORY_WARNING_ROWS + 1:
            logger.warning(
                "Large export detected: Excel/Polars export materializes review rows in memory. "
                "For very large games, use narrower filters or split the export into smaller runs."
            )
        rows.append(_normalize_review_for_export(raw_review, app_id))
    return rows


def process_reviews(reviews: Iterable[dict[str, Any]], app_id: int) -> "_pl.DataFrame":
    if pl is None:
        raise ImportError(
            "Polars is required to process reviews into DataFrames. "
            "Please install the library CLI dependencies using: pip install steam-review-exporter[cli]"
        )

    rows = _materialize_export_rows(reviews, app_id)
    df = pl.DataFrame(rows, infer_schema_length=1000)

    if not df.is_empty() and "review_url" in df.columns:
        cols = ["review_url"] + [c for c in df.columns if c != "review_url"]
        df = df.select(cols)

    return df


def save_to_excel(
    df: "_pl.DataFrame",
    app_id: int,
    game_name: str,
    language: str,
    filter_type: str = "all",
    min_len: int = 0,
    max_len: int | None = None,
    output_dir: str | Path | None = None,
) -> bool:
    if df.is_empty():
        logger.warning("No valid review data available to save.")
        return False

    filename = build_output_filename(game_name, language, filter_type, min_len, max_len)
    output_path = Path(filename)
    if output_dir is not None:
        output_path = Path(output_dir) / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df.write_excel(str(output_path))
        logger.info(f"Reviews successfully saved to: {output_path}")
        return True
    except PermissionError:
        logger.error(f"Error: Permission denied. The file '{output_path}' seems to be open in Excel.")
        logger.error("Please close the file and try again.")
        return False
    except ImportError as e:
        logger.error(f"Error: Missing dependency for Excel export. {e}")
        logger.error("Please install the CLI dependencies: pip install steam-review-exporter[cli]")
        return False
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return False
