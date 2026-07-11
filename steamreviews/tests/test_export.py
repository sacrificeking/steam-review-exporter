import logging
from pathlib import Path

import pytest

try:
    import polars as pl
except ImportError:
    pl = None  # type: ignore
from steamreviews.export import (
    filter_reviews_by_language,
    filter_reviews_by_length,
    process_reviews,
    sanitize_excel_text,
    save_to_excel,
)


def _review(recommendationid: str, text: str = "Great game!") -> dict:
    return {
        "recommendationid": recommendationid,
        "review": text,
        "voted_up": True,
        "votes_up": 10,
        "votes_funny": 2,
        "language": "english",
        "author": {
            "steamid": f"user{recommendationid}",
            "playtime_forever": 60,
            "playtime_last_two_weeks": 10,
            "playtime_at_review": 30,
        },
    }


def test_sanitize_excel_text_blocks_formula_prefixes():
    assert sanitize_excel_text("=CMD()") == "'=CMD()"
    assert sanitize_excel_text("+1234") == "'+1234"
    assert sanitize_excel_text("-1234") == "'-1234"
    assert sanitize_excel_text("@SUM(A1)") == "'@SUM(A1)"
    assert sanitize_excel_text("\tformula") == "'\tformula"
    assert sanitize_excel_text("\rformula") == "'\rformula"
    assert sanitize_excel_text("  =CMD()") == "'  =CMD()"
    assert sanitize_excel_text("normal text") == "normal text"


def test_filter_reviews_by_length():
    reviews = [{"review": "short"}, {"review": "this is a bit longer"}, {"review": "a very long review" * 10}]
    filtered = list(filter_reviews_by_length(reviews, min_len=10))
    assert len(filtered) == 2
    assert "short" not in [r["review"] for r in filtered]


def test_filter_reviews_by_language():
    reviews = [
        {"review": "short", "language": "english"},
        {"review": "dies ist ein deutscher test", "language": "german"},
    ]
    filtered = list(filter_reviews_by_language(reviews, "german"))
    assert len(filtered) == 1
    assert filtered[0]["language"] == "german"


def test_filter_reviews_by_language_logs_before_iteration(caplog):
    reviews = [{"review": "dies ist ein deutscher test", "language": "german"}]

    with caplog.at_level(logging.INFO):
        filtered = filter_reviews_by_language(reviews, "german", detector=lambda text: "de")

    assert "Applying content analysis for language 'german'" in caplog.text
    assert list(filtered) == reviews


def test_filter_reviews_by_length_logs_before_iteration(caplog):
    reviews = [{"review": "this is long enough"}]

    with caplog.at_level(logging.INFO):
        filtered = filter_reviews_by_length(reviews, min_len=10)

    assert "Applying length filter" in caplog.text
    assert list(filtered) == reviews


@pytest.mark.skipif(pl is None, reason="Polars is required for process_reviews test")
def test_process_reviews():
    reviews = [_review("123")]

    df = process_reviews(reviews, app_id=588650)
    assert len(df) == 1
    assert df["recommendationid"][0] == "123"
    assert df["review"][0] == "Great game!"


@pytest.mark.skipif(pl is None, reason="Polars is required for process_reviews test")
def test_process_reviews_warns_for_large_in_memory_export(monkeypatch, caplog):
    monkeypatch.setattr("steamreviews.export.EXPORT_MEMORY_WARNING_ROWS", 1)

    with caplog.at_level(logging.WARNING):
        df = process_reviews([_review("1"), _review("2")], app_id=588650)

    assert len(df) == 2
    assert "Large export detected" in caplog.text


@pytest.mark.skipif(pl is None, reason="Polars is required for process_reviews test")
def test_process_reviews_rejects_rows_above_excel_limit(monkeypatch):
    monkeypatch.setattr("steamreviews.export.MAX_EXCEL_DATA_ROWS", 1)

    with pytest.raises(ValueError, match="Excel export supports at most"):
        process_reviews([_review("1"), _review("2")], app_id=588650)


@pytest.mark.skipif(pl is None, reason="Polars is required for save_to_excel test")
def test_save_to_excel():
    import shutil
    import tempfile

    df = pl.DataFrame({"review": ["nice"]})
    tmp_path = tempfile.mkdtemp()
    result = save_to_excel(df, 123, "Game", "english", output_dir=tmp_path)
    assert result is True
    assert list(Path(tmp_path).glob("*.xlsx"))
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.mark.asyncio
async def test_fetch_reviews_reports_partial_outcome(monkeypatch):
    from unittest.mock import AsyncMock, patch

    from steamreviews.export import fetch_reviews
    from steamreviews.results import FetchOutcome

    async def mock_fetch_all(*args, **kwargs):
        return FetchOutcome(
            complete=False,
            downloaded_count=2,
            expected_total=100,
            failure_reason="API error during fetch: timeout",
        )

    with patch("steamreviews.export.SteamReviewScraper") as scraper_cls:
        scraper = scraper_cls.return_value
        scraper.fetch_all_reviews = AsyncMock(side_effect=mock_fetch_all)
        scraper.run_id = "run-1"
        scraper.storage.load_run_reviews.return_value = [
            {"recommendationid": "1", "review": "nice", "language": "english"},
            {"recommendationid": "2", "review": "also nice", "language": "english"},
        ]

        result = await fetch_reviews(123, "english")

    assert len(result.reviews) == 2
    assert result.outcome.partial is True
    assert result.outcome.failure_reason is not None


@pytest.mark.asyncio
async def test_fetch_reviews_uses_separate_cache_dir():
    import shutil
    import tempfile
    from unittest.mock import AsyncMock, MagicMock, patch

    from steamreviews.export import fetch_reviews
    from steamreviews.results import FetchOutcome

    cache_dir = tempfile.mkdtemp()

    with patch("steamreviews.storage.SQLiteStorage") as storage_cls:
        storage = MagicMock()
        storage.load_run_reviews.return_value = []
        storage_cls.return_value = storage

        with patch("steamreviews.export.SteamReviewScraper") as scraper_cls:
            scraper = scraper_cls.return_value
            scraper.fetch_all_reviews = AsyncMock(return_value=FetchOutcome(complete=True, downloaded_count=0))
            scraper.run_id = "run-1"
            scraper.storage = storage

            await fetch_reviews(123, "english", cache_dir=str(cache_dir))

    try:
        storage_cls.assert_called_once_with(data_dir=cache_dir)
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)


def test_parameterized_export_limits(monkeypatch):
    import importlib

    import steamreviews.export

    monkeypatch.setenv("STEAM_EXPORT_WARN_ROWS", "123")
    monkeypatch.setenv("STEAM_EXPORT_MAX_ROWS", "456")

    # Reload export module to capture new env variables
    importlib.reload(steamreviews.export)

    try:
        assert steamreviews.export.EXPORT_MEMORY_WARNING_ROWS == 123
        assert steamreviews.export.MAX_EXCEL_DATA_ROWS == 456
    finally:
        # Restore defaults
        monkeypatch.delenv("STEAM_EXPORT_WARN_ROWS", raising=False)
        monkeypatch.delenv("STEAM_EXPORT_MAX_ROWS", raising=False)
        importlib.reload(steamreviews.export)

    assert steamreviews.export.EXPORT_MEMORY_WARNING_ROWS == 250_000
    assert steamreviews.export.MAX_EXCEL_DATA_ROWS == 1_048_575
