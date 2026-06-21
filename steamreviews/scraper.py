import hashlib
import logging
import uuid

from tqdm import tqdm

from steamreviews.api import SteamAPIClient
from steamreviews.cache import SQLiteCache

logger = logging.getLogger(__name__)

class SteamReviewScraper:
    """Orchestrates the pagination and downloading of Steam reviews."""
    
    def __init__(self, data_dir: str | None = None):
        self.api = SteamAPIClient()
        self.cache = SQLiteCache(data_dir=data_dir if data_dir else "data")
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
        
        while True:
            # Check for infinite loops
            if cursor != "*" and self.cache.has_visited_cursor(app_id, params_hash, cursor):
                logger.warning(f"Cursor {cursor} already visited. Stopping to prevent infinite loop.")
                break
                
            self.cache.save_cursor(app_id, params_hash, cursor)

            response = await self.api.get_reviews(app_id, cursor, request_params)
            
            if response is None:
                logger.error("Failed to download reviews batch.")
                if pbar:
                    pbar.close()
                return False

            # First batch - initialize progress bar
            if num_reviews_expected is None and response.query_summary:
                self.cache.save_query_summary(app_id, response.query_summary.model_dump())
                num_reviews_expected = response.query_summary.total_reviews
                
                # If total_reviews is unreliable (e.g. strict filters), we could do a secondary wide query here
                # but for simplicity and performance, we'll trust the API for now, or just track downloaded count.
                if num_reviews_expected > 0:
                    pbar = tqdm(total=num_reviews_expected, desc=f"AppID {app_id}", unit="reviews")
                
            reviews_list = [r.model_dump() for r in response.reviews]
            delta = len(reviews_list)
            
            if delta > 0:
                self.cache.merge_reviews(self.run_id, app_id, reviews_list)
                offset += delta
                if pbar:
                    pbar.update(delta)
            
            # Stop condition
            if delta == 0 or response.cursor == cursor:
                break
                
            cursor = response.cursor

        if pbar:
            pbar.close()
            
        final_count = self.cache.get_review_count(app_id)
        logger.info(f"[appID = {app_id}] Total downloaded in cache: {final_count}")
        return True
