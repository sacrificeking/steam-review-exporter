import json
import logging
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class ReviewStorageProtocol(Protocol):
    """
    Protocol defining the interface for storing Steam reviews and tracking scraper progress.
    """

    def merge_reviews(self, run_id: str, app_id: int, reviews: list[dict[str, Any]]) -> None: ...

    def save_cursor(self, app_id: int, params_hash: str, cursor_str: str) -> None: ...

    def has_visited_cursor(self, app_id: int, params_hash: str, cursor_str: str) -> bool: ...

    def save_query_summary(self, app_id: int, query_summary: dict[str, Any]) -> None: ...

    def load_query_summary(self, app_id: int) -> dict[str, Any] | None: ...

    def load_run_reviews(self, run_id: str, app_id: int) -> Iterable[dict[str, Any]]: ...

    def get_review_count(self, app_id: int) -> int: ...


class SQLiteStorage:
    """
    SQLite-based local cache for Steam reviews.
    Used primarily for the CLI tool to allow resumable downloads without repeated network work.
    """

    def __init__(self, data_dir: Path | str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "steam_reviews.db"
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")

                # Migrate cursors table if params_hash column is missing from older schema versions
                cursor.execute("PRAGMA table_info(cursors);")
                columns = [row[1] for row in cursor.fetchall()]
                if columns and "params_hash" not in columns:
                    logger.info("Upgrading SQLite database: recreating cursors table with params_hash support.")
                    cursor.execute("DROP TABLE IF EXISTS cursors;")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reviews (
                        app_id INTEGER,
                        recommendationid TEXT,
                        data_json TEXT,
                        PRIMARY KEY (app_id, recommendationid)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cursors (
                        app_id INTEGER,
                        params_hash TEXT,
                        cursor TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (app_id, params_hash, cursor)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS run_reviews (
                        run_id TEXT,
                        app_id INTEGER,
                        recommendationid TEXT,
                        PRIMARY KEY (run_id, app_id, recommendationid)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS query_summaries (
                        app_id INTEGER PRIMARY KEY,
                        data_json TEXT
                    )
                """)
                conn.commit()
        finally:
            conn.close()

    def get_existing_review_ids(self, app_id: int) -> set[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT recommendationid FROM reviews WHERE app_id = ?", (app_id,))
            return {row[0] for row in cursor.fetchall()}
        finally:
            conn.close()

    def merge_reviews(self, run_id: str, app_id: int, reviews: list[dict[str, Any]]) -> None:
        if not reviews:
            return

        data_to_insert: list[tuple[int, str, str]] = []
        run_data: list[tuple[str, int, str]] = []
        for review in reviews:
            recommendation_id = review.get("recommendationid")
            if recommendation_id is None:
                logger.warning("Skipping review without recommendationid for app_id=%s", app_id)
                continue
            recommendation_id_str = str(recommendation_id)
            data_to_insert.append((app_id, recommendation_id_str, json.dumps(review)))
            run_data.append((run_id, app_id, recommendation_id_str))

        if not data_to_insert:
            return

        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO reviews (app_id, recommendationid, data_json)
                    VALUES (?, ?, ?)
                """,
                    data_to_insert,
                )
                cursor.executemany(
                    """
                    INSERT OR IGNORE INTO run_reviews (run_id, app_id, recommendationid)
                    VALUES (?, ?, ?)
                """,
                    run_data,
                )
                conn.commit()
        finally:
            conn.close()

    def save_cursor(self, app_id: int, params_hash: str, cursor_str: str) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO cursors (app_id, params_hash, cursor)
                    VALUES (?, ?, ?)
                """,
                    (app_id, params_hash, cursor_str),
                )
                conn.commit()
        finally:
            conn.close()

    def has_visited_cursor(self, app_id: int, params_hash: str, cursor_str: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1 FROM cursors WHERE app_id = ? AND params_hash = ? AND cursor = ?
            """,
                (app_id, params_hash, cursor_str),
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def save_query_summary(self, app_id: int, query_summary: dict[str, Any]) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO query_summaries (app_id, data_json)
                    VALUES (?, ?)
                """,
                    (app_id, json.dumps(query_summary)),
                )
                conn.commit()
        finally:
            conn.close()

    def load_query_summary(self, app_id: int) -> dict[str, Any] | None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT data_json FROM query_summaries WHERE app_id = ?", (app_id,))
            row = cursor.fetchone()
            if row:
                res: dict[str, Any] = json.loads(row[0])
                return res
            return None
        finally:
            conn.close()

    def load_run_reviews(self, run_id: str, app_id: int) -> list[dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.data_json 
                FROM reviews r
                JOIN run_reviews rr ON r.app_id = rr.app_id AND r.recommendationid = rr.recommendationid
                WHERE rr.run_id = ? AND r.app_id = ?
                """,
                (run_id, app_id),
            )
            return [json.loads(row[0]) for row in cursor]
        finally:
            conn.close()

    def get_review_count(self, app_id: int) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM reviews WHERE app_id = ?", (app_id,))
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()


class MemoryStorage:
    """
    In-Memory Storage for Steam Reviews.
    Useful for Web/Edge environments where persistence is not required locally,
    or where data is streamed and discarded.
    """

    def __init__(self) -> None:
        self.reviews: list[dict[str, Any]] = []
        self.cursors_visited: set[tuple[int, str, str]] = set()
        self.query_summaries: dict[int, dict[str, Any]] = {}

    def merge_reviews(self, run_id: str, app_id: int, reviews: list[dict[str, Any]]) -> None:
        self.reviews.extend(reviews)

    def save_cursor(self, app_id: int, params_hash: str, cursor_str: str) -> None:
        self.cursors_visited.add((app_id, params_hash, cursor_str))

    def has_visited_cursor(self, app_id: int, params_hash: str, cursor_str: str) -> bool:
        return (app_id, params_hash, cursor_str) in self.cursors_visited

    def save_query_summary(self, app_id: int, query_summary: dict[str, Any]) -> None:
        self.query_summaries[app_id] = query_summary

    def load_query_summary(self, app_id: int) -> dict[str, Any] | None:
        return self.query_summaries.get(app_id)

    def load_run_reviews(self, run_id: str, app_id: int) -> Iterable[dict[str, Any]]:
        yield from self.reviews

    def get_review_count(self, app_id: int) -> int:
        return len(self.reviews)


class NullStorage:
    """
    No-op storage. Ideal for scenarios where the consumer uses fetch_reviews_stream
    and handles its own storage/persistence externally.
    Cursor tracking is kept in-memory to prevent loops during the single run.
    """

    def __init__(self) -> None:
        self.cursors_visited: set[tuple[int, str, str]] = set()
        self.query_summaries: dict[int, dict[str, Any]] = {}

    def merge_reviews(self, run_id: str, app_id: int, reviews: list[dict[str, Any]]) -> None:
        pass

    def save_cursor(self, app_id: int, params_hash: str, cursor_str: str) -> None:
        self.cursors_visited.add((app_id, params_hash, cursor_str))

    def has_visited_cursor(self, app_id: int, params_hash: str, cursor_str: str) -> bool:
        return (app_id, params_hash, cursor_str) in self.cursors_visited

    def save_query_summary(self, app_id: int, query_summary: dict[str, Any]) -> None:
        self.query_summaries[app_id] = query_summary

    def load_query_summary(self, app_id: int) -> dict[str, Any] | None:
        return self.query_summaries.get(app_id)

    def load_run_reviews(self, run_id: str, app_id: int) -> Iterable[dict[str, Any]]:
        yield from []

    def get_review_count(self, app_id: int) -> int:
        return 0
