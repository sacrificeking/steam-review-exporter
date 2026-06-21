import sqlite3
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Set, Optional

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
        with sqlite3.connect(self.db_path) as conn:
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
                    cursor TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (app_id, cursor)
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

    def get_existing_review_ids(self, app_id: int) -> Set[str]:
        """Returns a set of all recommendation IDs already downloaded for this AppID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT recommendationid FROM reviews WHERE app_id = ?', (app_id,))
            return {row[0] for row in cursor.fetchall()}

    def merge_reviews(self, app_id: int, reviews: List[Dict[str, Any]]) -> None:
        """Inserts multiple reviews efficiently using executemany."""
        if not reviews:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            data_to_insert = [
                (app_id, str(r["recommendationid"]), json.dumps(r))
                for r in reviews
            ]
            # Use REPLACE to update existing reviews if they changed, or IGNORE
            cursor.executemany('''
                INSERT OR REPLACE INTO reviews (app_id, recommendationid, data_json)
                VALUES (?, ?, ?)
            ''', data_to_insert)
            conn.commit()

    def save_cursor(self, app_id: int, cursor_str: str) -> None:
        """Records a cursor as visited."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO cursors (app_id, cursor)
                VALUES (?, ?)
            ''', (app_id, cursor_str))
            conn.commit()

    def has_visited_cursor(self, app_id: int, cursor_str: str) -> bool:
        """Checks if a cursor has already been visited (prevents infinite loops)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM cursors WHERE app_id = ? AND cursor = ?
            ''', (app_id, cursor_str))
            return cursor.fetchone() is not None

    def save_query_summary(self, app_id: int, query_summary: Dict[str, Any]) -> None:
        """Saves the latest query summary for the AppID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO query_summaries (app_id, data_json)
                VALUES (?, ?)
            ''', (app_id, json.dumps(query_summary)))
            conn.commit()

    def load_query_summary(self, app_id: int) -> Optional[Dict[str, Any]]:
        """Loads the saved query summary for the AppID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data_json FROM query_summaries WHERE app_id = ?', (app_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None

    def load_all_reviews(self, app_id: int) -> List[Dict[str, Any]]:
        """Loads all reviews for a given AppID into memory (used during export)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data_json FROM reviews WHERE app_id = ?', (app_id,))
            return [json.loads(row[0]) for row in cursor.fetchall()]

    def get_review_count(self, app_id: int) -> int:
        """Returns the number of downloaded reviews for the AppID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM reviews WHERE app_id = ?', (app_id,))
            row = cursor.fetchone()
            return row[0] if row else 0
