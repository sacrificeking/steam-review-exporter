import asyncio
import logging

import httpx

from steamreviews.models import SteamApiResponse

logger = logging.getLogger(__name__)

class SteamAPIError(Exception):
    """Exception raised when the Steam API fails to return valid data after retries."""
    pass

class SteamAPIClient:
    """Async HTTP client for Steam API using httpx."""
    
    BASE_URL = "https://store.steampowered.com/appreviews/"
    RATE_LIMIT_COOLDOWN = 300  # 5 minutes
    INITIAL_BACKOFF = 2.0
    MAX_RETRIES = 5
    MAX_QUERIES = 150
    
    def __init__(self) -> None:
        self.headers = {"User-Agent": "steam-review-exporter/1.1"}
        self.timeout = httpx.Timeout(5.0, read=30.0)
        self._query_count = 0

    async def get_reviews(self, app_id: int, cursor: str, request_params: dict[str, str]) -> SteamApiResponse | None:
        """Fetches a single batch of reviews from the Steam API."""
        if self._query_count >= self.MAX_QUERIES:
            logger.warning(f"Rate limit reached ({self.MAX_QUERIES} queries). Cooling down for {self.RATE_LIMIT_COOLDOWN}s...")
            await asyncio.sleep(self.RATE_LIMIT_COOLDOWN)
            self._query_count = 0

        url = f"{self.BASE_URL}{app_id}"
        params = dict(request_params)
        params["cursor"] = cursor

        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            retries = 0
            while retries <= self.MAX_RETRIES:
                try:
                    response = await client.get(url, params=params)
                    self._query_count += 1
                    
                    if response.status_code in (429, 500, 502, 503, 504):
                        retries += 1
                        if retries > self.MAX_RETRIES:
                            raise SteamAPIError(f"Steam API returned {response.status_code} and exceeded max retries.")
                        backoff = self.INITIAL_BACKOFF * (2 ** (retries - 1))
                        logger.warning(f"Steam API returned {response.status_code}. Retrying in {backoff}s ({retries}/{self.MAX_RETRIES})...")
                        await asyncio.sleep(backoff)
                        continue
                        
                    response.raise_for_status()
                    
                    data = response.json()
                    # Validate and sanitize incoming data via Pydantic model
                    return SteamApiResponse.model_validate(data)
                    
                except httpx.RequestError as e:
                    retries += 1
                    if retries > self.MAX_RETRIES:
                        raise SteamAPIError(f"Network error while fetching reviews for {app_id}: {e}") from e
                    backoff = self.INITIAL_BACKOFF * (2 ** (retries - 1))
                    logger.warning(f"Network error: {e}. Retrying in {backoff}s ({retries}/{self.MAX_RETRIES})...")
                    await asyncio.sleep(backoff)
                except SteamAPIError:
                    raise
                except Exception as e:
                    logger.error(f"Error parsing Steam API response for {app_id}: {e}")
                    return None
            
            raise SteamAPIError(f"Failed to fetch reviews for {app_id} after {self.MAX_RETRIES} retries.")
