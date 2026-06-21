import contextlib
import shutil
import tempfile

import pytest

from steamreviews.storage import SQLiteStorage


@pytest.fixture
def temp_cache():
    dir_path = tempfile.mkdtemp()
    yield SQLiteStorage(data_dir=dir_path)
    with contextlib.suppress(OSError):
        shutil.rmtree(dir_path, ignore_errors=True)


def test_cache_init(temp_cache):
    assert temp_cache.db_path.exists()


def test_cache_merge_and_load(temp_cache):
    reviews = [{"recommendationid": "1", "review": "nice"}]
    temp_cache.merge_reviews("run1", 123, reviews)

    count = temp_cache.get_review_count(123)
    assert count == 1, "Review count should be 1"

    run_reviews = temp_cache.load_run_reviews("run1", 123)
    assert len(run_reviews) == 1
    assert run_reviews[0]["recommendationid"] == "1"


def test_cache_cursor_tracking(temp_cache):
    temp_cache.save_cursor(123, "hash", "cursor1")
    assert temp_cache.has_visited_cursor(123, "hash", "cursor1") is True
    assert temp_cache.has_visited_cursor(123, "hash", "cursor2") is False


def test_cache_query_summary(temp_cache):
    summary = {"total_reviews": 100}
    temp_cache.save_query_summary(123, summary)

    loaded = temp_cache.load_query_summary(123)
    assert loaded == summary
