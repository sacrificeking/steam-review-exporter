import asyncio
import logging
import httpx
from typing import Dict, Any, Optional
from steamreviews.models import SteamApiResponse

logger = logging.getLogger(__name__)

class SteamAPIClient:
    """Async HTTP client for Steam API using httpx."""
    
    BASE_URL = "https://store.steampowered.com/appreviews/"
    RATE_LIMIT_COOLDOWN = 300  # 5 minutes
    BAD_GATEWAY_COOLDOWN = 10
    MAX_QUERIES = 150
    
    def __init__(self) -> None:
        self.headers = {"User-Agent": "steam-review-exporter/1.1"}
        self.timeout = httpx.Timeout(5.0, read=30.0)
        self._query_count = 0

    async def get_reviews(self, app_id: int, cursor: str, request_params: Dict[str, str]) -> Optional[SteamApiResponse]:
        """Fetches a single batch of reviews from the Steam API."""
        if self._query_count >= self.MAX_QUERIES:
            logger.warning(f"Rate limit reached ({self.MAX_QUERIES} queries). Cooling down for {self.RATE_LIMIT_COOLDOWN}s...")
            await asyncio.sleep(self.RATE_LIMIT_COOLDOWN)
            self._query_count = 0

        url = f"{self.BASE_URL}{app_id}"
        params = dict(request_params)
        params["cursor"] = cursor

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            while True:
                try:
                    response = await client.get(url, params=params)
                    self._query_count += 1
                    
                    if response.status_code in (429, 500, 502, 503, 504):
                        logger.warning(f"Steam API returned {response.status_code}. Retrying in {self.BAD_GATEWAY_COOLDOWN}s...")
                        await asyncio.sleep(self.BAD_GATEWAY_COOLDOWN)
                        continue
                        
                    response.raise_for_status()
                    
                    data = response.json()
                    # Validate and sanitize incoming data via Pydantic model
                    return SteamApiResponse.model_validate(data)
                    
                except httpx.RequestError as e:
                    logger.error(f"Network error while fetching reviews for {app_id}: {e}")
                    return None
                except Exception as e:
                    logger.error(f"Error parsing Steam API response for {app_id}: {e}")
                    return None
