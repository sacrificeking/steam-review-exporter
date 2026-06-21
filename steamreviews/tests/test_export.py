import pytest
from steamreviews.export import filter_reviews_by_language, filter_reviews_by_length, process_reviews, save_to_excel
import polars as pl
from pathlib import Path

def test_filter_reviews_by_length():
    reviews = [
        {"review": "short"},
        {"review": "this is a very long review indeed"}
    ]
    filtered = filter_reviews_by_length(reviews, min_len=10)
    assert len(filtered) == 1
    assert filtered[0]["review"] == "this is a very long review indeed"

def test_filter_reviews_by_language():
    reviews = [
        {"review": "short", "language": "english"},
        {"review": "dies ist ein deutscher test", "language": "german"}
    ]
    
    filtered = filter_reviews_by_language(reviews, "german")
    assert len(filtered) == 1
    assert filtered[0]["language"] == "german"

def test_process_reviews():
    reviews = [
        {
            "review": "=1+1",
            "author": {"steamid": "123"}
        }
    ]
    
    df = process_reviews(reviews, 10)
    assert len(df) == 1
    assert df["review"][0] == "'=1+1"
    assert df["author_steamid"][0] == "123"

def test_save_to_excel():
    import tempfile
    import shutil
    df = pl.DataFrame({"review": ["nice"]})
    tmp_path = tempfile.mkdtemp()
    result = save_to_excel(df, 123, "Game", "english", output_dir=tmp_path)
    assert result is True
    assert list(Path(tmp_path).glob("*.xlsx"))
    shutil.rmtree(tmp_path, ignore_errors=True)
