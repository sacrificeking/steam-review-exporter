from pathlib import Path

import pytest

try:
    import polars as pl
except ImportError:
    pl = None  # type: ignore
from steamreviews.export import filter_reviews_by_language, filter_reviews_by_length, process_reviews, save_to_excel


def test_filter_reviews_by_length():
    reviews = [{"review": "short"}, {"review": "this is a very long review indeed"}]
    filtered = filter_reviews_by_length(reviews, min_len=10)
    assert len(filtered) == 1
    assert filtered[0]["review"] == "this is a very long review indeed"


def test_filter_reviews_by_language():
    reviews = [
        {"review": "short", "language": "english"},
        {"review": "dies ist ein deutscher test", "language": "german"},
    ]

    filtered = filter_reviews_by_language(reviews, "german")
    assert len(filtered) == 1
    assert filtered[0]["language"] == "german"


@pytest.mark.skipif(pl is None, reason="Polars is required for process_reviews test")
def test_process_reviews():
    reviews = [
        {
            "recommendationid": "123",
            "review": "Great game!",
            "voted_up": True,
            "votes_up": 10,
            "votes_funny": 2,
            "language": "english",
            "author": {
                "steamid": "user1",
                "playtime_forever": 60,
                "playtime_last_two_weeks": 10,
                "playtime_at_review": 30,
            },
        }
    ]

    df = process_reviews(reviews, app_id=588650)
    assert len(df) == 1
    assert df["recommendationid"][0] == "123"
    assert df["review"][0] == "Great game!"


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
