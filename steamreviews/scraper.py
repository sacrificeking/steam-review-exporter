import hashlib
import logging
import uuid

from tqdm import tqdm

from steamreviews.api import SteamAPIClient, SteamAPIError
from steamreviews.storage import ReviewStorageProtocol, SQLiteStorage

logger = logging.getLogger(__name__)


class SteamCursorLoopError(Exception):
    """Raised when the scraper detects an infinite pagination loop."""

    pass


class SteamReviewScraper:
    """Orchestrates the pagination and downloading of Steam reviews."""

    def __init__(self, storage: ReviewStorageProtocol | None = None, data_dir: str | None = None):
        self.api = SteamAPIClient()
        if storage is not None:
            self.storage = storage
        else:
            # Fallback to SQLite for backward compatibility if no storage injected
            self.storage = SQLiteStorage(data_dir=data_dir if data_dir else "data")
        self.run_id: str = ""

    async def fetch_all_reviews(self, app_id: int, request_params: dict[str, str]) -> bool:
        """
        Fetches all reviews for a given AppID, handling pagination and rate limits.
        Uses SQLite for incremental caching.
        Returns True if successful.
        """
        cursor = "*"
        num_reviews_expected = None
        offset = 0
        pbar = None

        self.run_id = str(uuid.uuid4())

        # Create a stable hash of the request parameters
        params_str = ",".join(f"{k}={v}" for k, v in sorted(request_params.items()))
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()

        logger.info(f"Downloading reviews for AppID = {app_id} (Run: {self.run_id[:8]})")

        try:
            async with self.api:
                while True:
                    # Check for infinite loops
                    if cursor != "*" and self.storage.has_visited_cursor(app_id, params_hash, cursor):
                        logger.error(f"Cursor {cursor} already visited. Stopping to prevent infinite loop.")
                        raise SteamCursorLoopError(f"Infinite loop detected at cursor {cursor}")

                    self.storage.save_cursor(app_id, params_hash, cursor)

                    try:
                        response = await self.api.get_reviews(app_id, cursor, request_params)
                    except SteamAPIError as e:
                        logger.error(f"API Error during fetch: {e}")
                        return False

                    # First batch - initialize progress bar
                    if num_reviews_expected is None and response.query_summary:
                        self.storage.save_query_summary(app_id, response.query_summary.model_dump())
                        num_reviews_expected = response.query_summary.total_reviews

                        # If total_reviews is unreliable, a secondary wide query could refine it.
                        # For now, trust the API or just track downloaded count.
                        if num_reviews_expected > 0:
                            pbar = tqdm(total=num_reviews_expected, desc=f"AppID {app_id}", unit="reviews")

                    reviews_list = [r.model_dump() for r in response.reviews]
                    delta = len(reviews_list)

                    if delta > 0:
                        self.storage.merge_reviews(self.run_id, app_id, reviews_list)
                        offset += delta
                        if pbar:
                            pbar.update(delta)

                    # Stop condition
                    if delta == 0 or response.cursor == cursor:
                        break

                    cursor = response.cursor
        finally:
            if pbar:
                pbar.close()

        final_count = self.storage.get_review_count(app_id)
        logger.info(f"[appID = {app_id}] Total downloaded in cache: {final_count}")
        return True

    async def fetch_reviews_stream(self, app_id: int, request_params: dict[str, str]):
        """
        Fetches all reviews for a given AppID and yields them batch by batch.
        Ideal for Web/Edge streaming without loading all data into memory or SQLite.
        """
        cursor = "*"
        self.run_id = str(uuid.uuid4())

        params_str = ",".join(f"{k}={v}" for k, v in sorted(request_params.items()))
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()

        logger.info(f"Streaming reviews for AppID = {app_id} (Run: {self.run_id[:8]})")

        async with self.api:
            while True:
                if cursor != "*" and self.storage.has_visited_cursor(app_id, params_hash, cursor):
                    logger.error(f"Cursor {cursor} already visited. Breaking stream due to loop.")
                    raise SteamCursorLoopError(f"Infinite loop detected at cursor {cursor}")

                self.storage.save_cursor(app_id, params_hash, cursor)

                # We don't catch exceptions here. They bubble up to the consumer (e.g. Edge Function)
                response = await self.api.get_reviews(app_id, cursor, request_params)

                if response.query_summary:
                    self.storage.save_query_summary(app_id, response.query_summary.model_dump())

                reviews_list = [r.model_dump() for r in response.reviews]
                if reviews_list:
                    self.storage.merge_reviews(self.run_id, app_id, reviews_list)
                    yield reviews_list

                if len(reviews_list) == 0 or response.cursor == cursor:
                    break

                cursor = response.cursor
