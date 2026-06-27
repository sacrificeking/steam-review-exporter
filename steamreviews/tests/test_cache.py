import contextlib
import shutil
import tempfile
import threading

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
    import sqlite3

    conn = sqlite3.connect(temp_cache.db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"
    finally:
        conn.close()


def test_cache_merge_and_load(temp_cache):
    reviews = [{"recommendationid": "1", "review": "nice"}]
    temp_cache.merge_reviews("run1", 123, reviews)

    assert temp_cache.get_review_count(123) == 1
    new_reviews = [{"recommendationid": "3", "review": "nice"}]
    temp_cache.merge_reviews("run1", 123, new_reviews)

    run_reviews = list(temp_cache.load_run_reviews("run1", 123))
    assert len(run_reviews) == 2
    ids = {r["recommendationid"] for r in run_reviews}
    assert "1" in ids and "3" in ids


def test_cache_loaded_reviews_are_thread_safe_after_partial_iteration(temp_cache):
    reviews = [
        {"recommendationid": "1", "review": "nice"},
        {"recommendationid": "2", "review": "also nice"},
    ]
    temp_cache.merge_reviews("run1", 123, reviews)

    loaded_reviews = temp_cache.load_run_reviews("run1", 123)
    iterator = iter(loaded_reviews)
    assert next(iterator)["recommendationid"] in {"1", "2"}

    remaining_reviews = []
    errors = []

    def consume_remaining() -> None:
        try:
            remaining_reviews.extend(iterator)
        except Exception as exc:  # pragma: no cover - failure is asserted below
            errors.append(exc)

    thread = threading.Thread(target=consume_remaining)
    thread.start()
    thread.join(timeout=5)

    assert errors == []
    assert len(remaining_reviews) == 1


def test_cache_cursor_tracking(temp_cache):
    temp_cache.save_cursor(123, "hash", "cursor1")
    assert temp_cache.has_visited_cursor(123, "hash", "cursor1") is True
    assert temp_cache.has_visited_cursor(123, "hash", "cursor2") is False


def test_cache_query_summary(temp_cache):
    summary = {"total_reviews": 100}
    temp_cache.save_query_summary(123, summary)

    loaded = temp_cache.load_query_summary(123)
    assert loaded == summary


def test_cache_migration_recreates_cursors_table(temp_cache, caplog):
    import logging
    import sqlite3

    db_path = temp_cache.db_path

    # Drop and recreate standard old cursors table
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS cursors;")
            cursor.execute("""
                CREATE TABLE cursors (
                    app_id INTEGER,
                    cursor TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (app_id, cursor)
                )
            """)
    finally:
        conn.close()

    # Re-initializing SQLiteStorage on the same db path should trigger migration
    with caplog.at_level(logging.INFO):
        SQLiteStorage(data_dir=temp_cache.data_dir)

    assert "recreating cursors table" in caplog.text

    # Verify new schema is applied
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(cursors);")
        columns = [row[1] for row in cursor.fetchall()]
        assert "params_hash" in columns
    finally:
        conn.close()
