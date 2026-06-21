import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class SQLiteCache:
    """
    SQLite-based local cache for Steam reviews.
    Replaces massive JSON files with incremental SQLite inserts for performance.
    """
    def __init__(self, data_dir: Path | str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "steam_reviews.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initializes the database schema."""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.cursor()
                # Reviews table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS reviews (
                        app_id INTEGER,
                        recommendationid TEXT,
                        data_json TEXT,
                        PRIMARY KEY (app_id, recommendationid)
                    )
                ''')
            # Cursors table (tracks visited cursors to prevent loops)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cursors (
                    app_id INTEGER,
                    params_hash TEXT,
                    cursor TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (app_id, params_hash, cursor)
                )
            ''')
            # Run reviews table (tracks which reviews were seen in which run)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS run_reviews (
                    run_id TEXT,
                    app_id INTEGER,
                    recommendationid TEXT,
                    PRIMARY KEY (run_id, app_id, recommendationid)
                )
            ''')
            # Query summary table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS query_summaries (
                    app_id INTEGER PRIMARY KEY,
                    data_json TEXT
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    def get_existing_review_ids(self, app_id: int) -> set[str]:
        """Returns a set of all recommendation IDs already downloaded for this AppID."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT recommendationid FROM reviews WHERE app_id = ?', (app_id,))
            return {row[0] for row in cursor.fetchall()}
        finally:
            conn.close()

    def merge_reviews(self, run_id: str, app_id: int, reviews: list[dict[str, Any]]) -> None:
        """Inserts multiple reviews efficiently using executemany, and links them to the run_id."""
        if not reviews:
            return
            
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.cursor()
                data_to_insert = [
                    (app_id, str(r["recommendationid"]), json.dumps(r))
                    for r in reviews
                ]
            cursor.executemany('''
                INSERT OR REPLACE INTO reviews (app_id, recommendationid, data_json)
                VALUES (?, ?, ?)
            ''', data_to_insert)
            
            run_data = [
                (run_id, app_id, str(r["recommendationid"]))
                for r in reviews
            ]
            cursor.executemany('''
                INSERT OR IGNORE INTO run_reviews (run_id, app_id, recommendationid)
                VALUES (?, ?, ?)
            ''', run_data)
            conn.commit()
        finally:
            conn.close()

    def save_cursor(self, app_id: int, params_hash: str, cursor_str: str) -> None:
        """Records a cursor as visited for a specific query configuration."""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO cursors (app_id, params_hash, cursor)
                    VALUES (?, ?, ?)
                ''', (app_id, params_hash, cursor_str))
                conn.commit()
        finally:
            conn.close()

    def has_visited_cursor(self, app_id: int, params_hash: str, cursor_str: str) -> bool:
        """Checks if a cursor has already been visited (prevents infinite loops)."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM cursors WHERE app_id = ? AND params_hash = ? AND cursor = ?
            ''', (app_id, params_hash, cursor_str))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def save_query_summary(self, app_id: int, query_summary: dict[str, Any]) -> None:
        """Saves the latest query summary for the AppID."""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO query_summaries (app_id, data_json)
                    VALUES (?, ?)
                ''', (app_id, json.dumps(query_summary)))
                conn.commit()
        finally:
            conn.close()

    def load_query_summary(self, app_id: int) -> dict[str, Any] | None:
        """Loads the saved query summary for the AppID."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT data_json FROM query_summaries WHERE app_id = ?', (app_id,))
            row = cursor.fetchone()
            if row:
                res: dict[str, Any] = json.loads(row[0])
                return res
            return None
        finally:
            conn.close()

    def load_run_reviews(self, run_id: str, app_id: int) -> list[dict[str, Any]]:
        """Loads only the reviews fetched during a specific run_id."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.data_json 
                FROM reviews r
                JOIN run_reviews rr ON r.app_id = rr.app_id AND r.recommendationid = rr.recommendationid
                WHERE rr.run_id = ? AND r.app_id = ?
            ''', (run_id, app_id))
            return [json.loads(row[0]) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_review_count(self, app_id: int) -> int:
        """Returns the number of downloaded reviews for the AppID."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM reviews WHERE app_id = ?', (app_id,))
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
