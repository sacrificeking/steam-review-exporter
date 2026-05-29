from unittest.mock import patch

import pandas as pd

from steamreviews.export import (
    build_output_filename,
    fetch_reviews,
    process_reviews,
    sanitize_excel_text,
    sanitize_filename_part,
    save_to_excel,
)


def test_sanitize_filename_part_removes_unsafe_characters():
    assert sanitize_filename_part("Dead: Cells? / Deluxe!") == "Dead Cells  Deluxe"
    assert sanitize_filename_part("!!!") == "unknown"


def test_sanitize_excel_text_prefixes_formula_like_values():
    for value in ("=SUM(1,1)", "+cmd", "-cmd", "@cmd", "\tcmd", "\rcmd"):
        assert sanitize_excel_text(value) == "'" + value

    assert sanitize_excel_text("regular review") == "regular review"


def test_process_reviews_adds_url_and_sanitizes_review_text():
    reviews = [
        {
            "recommendationid": "1",
            "review": "=SUM(1,1)",
            "author": {"steamid": "76561198000000000"},
        },
        {
            "recommendationid": "2",
            "review": "Plain text",
            "author": {},
        },
    ]

    df = process_reviews(reviews, app_id=588650)

    assert list(df.columns)[0] == "review_url"
    assert df.loc[0, "review"] == "'=SUM(1,1)"
    assert df.loc[0, "review_url"] == "https://steamcommunity.com/profiles/76561198000000000/recommended/588650/"
    assert df.loc[1, "review_url"] == ""
    assert reviews[0]["review"] == "=SUM(1,1)"


@patch("steamreviews.export.detect")
@patch("steamreviews.export.steamreviews.download_reviews_for_app_id")
def test_fetch_reviews_filters_by_metadata_content_and_length(mock_download, mock_detect):
    mock_download.return_value = (
        {
            "reviews": {
                "1": {"recommendationid": "1", "language": "english", "review": "This game is really excellent."},
                "2": {"recommendationid": "2", "language": "english", "review": "Dieses Spiel ist wirklich gut."},
                "3": {"recommendationid": "3", "language": "german", "review": "Dieses Spiel ist gut."},
                "4": {"recommendationid": "4", "language": "english", "review": "ok"},
            },
        },
        1,
    )
    mock_detect.side_effect = ["en", "de"]

    reviews = fetch_reviews(588650, "english", min_len=10)

    assert [review["recommendationid"] for review in reviews] == ["1"]


def test_build_output_filename_includes_filter_and_length_details():
    assert build_output_filename("Dead: Cells?", "english") == "Dead Cells EN - Reviews full.xlsx"
    assert (
        build_output_filename("Dead Cells", "german", filter_type="recent", min_len=100, max_len=500)
        == "Dead Cells DE - Reviews recent len-100-500.xlsx"
    )


@patch.object(pd.DataFrame, "to_excel")
def test_save_to_excel_uses_built_filename(mock_to_excel):
    df = pd.DataFrame([{"review": "Nice"}])

    save_to_excel(df, 588650, "Dead: Cells?", "english", filter_type="recent", min_len=100, max_len=None)

    mock_to_excel.assert_called_once_with("Dead Cells EN - Reviews recent len-100-max.xlsx", index=False)


@patch.object(pd.DataFrame, "to_excel")
def test_save_to_excel_supports_output_dir(mock_to_excel, tmp_path):
    df = pd.DataFrame([{"review": "Nice"}])

    save_to_excel(df, 588650, "Dead Cells", "english", output_dir=tmp_path)

    mock_to_excel.assert_called_once_with(str(tmp_path / "Dead Cells EN - Reviews full.xlsx"), index=False)
