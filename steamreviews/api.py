import asyncio
import logging

import httpx
from pydantic import ValidationError

from steamreviews.models import SteamApiResponse

logger = logging.getLogger(__name__)


class SteamAPIError(Exception):
    """Base exception for Steam API errors."""

    pass


class SteamRateLimitError(SteamAPIError):
    """Raised when Steam API rate limit (HTTP 429) is hit and raise_on_rate_limit is True."""

    pass


class SteamUnavailableError(SteamAPIError):
    """Raised when Steam API is unavailable after max retries."""

    pass


class SteamValidationError(SteamAPIError):
    """Raised when the API response data is invalid or cannot be parsed."""

    pass


class SteamAPIClient:
    """Async HTTP client for Steam API using httpx."""

    BASE_URL = "https://store.steampowered.com/appreviews/"
    RATE_LIMIT_COOLDOWN = 300  # 5 minutes
    INITIAL_BACKOFF = 2.0
    MAX_RETRIES = 5
    MAX_QUERIES = 150

    def __init__(self, raise_on_rate_limit: bool = False) -> None:
        self.headers = {"User-Agent": "steam-review-exporter/1.1"}
        self.timeout = httpx.Timeout(5.0, read=30.0)
        self._query_count = 0
        self.raise_on_rate_limit = raise_on_rate_limit

    async def get_reviews(self, app_id: int, cursor: str, request_params: dict[str, str]) -> SteamApiResponse:
        """Fetches a single batch of reviews from the Steam API."""
        if self._query_count >= self.MAX_QUERIES:
            if self.raise_on_rate_limit:
                raise SteamRateLimitError(f"Rate limit reached ({self.MAX_QUERIES} queries).")
            logger.warning(
                f"Rate limit reached ({self.MAX_QUERIES} queries). Cooling down for {self.RATE_LIMIT_COOLDOWN}s..."
            )
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

                    if response.status_code == 200:
                        try:
                            data = response.json()
                        except ValueError as e:
                            logger.error(f"Steam API JSON parse error: {e}")
                            raise SteamValidationError(f"Failed to parse JSON: {e}") from e

                        try:
                            return SteamApiResponse.model_validate(data)
                        except ValidationError as e:
                            logger.error(f"Steam API validation error: {e}")
                            raise SteamValidationError(f"Failed to validate response against model: {e}") from e

                    elif response.status_code == 429:
                        if self.raise_on_rate_limit:
                            raise SteamRateLimitError("Steam API returned HTTP 429 Too Many Requests.")
                        logger.warning("Steam API returned HTTP 429. Cooling down.")
                        await asyncio.sleep(self.RATE_LIMIT_COOLDOWN)
                        self._query_count = 0
                        continue

                    elif response.status_code in (500, 502, 503, 504):
                        retries += 1
                        if retries > self.MAX_RETRIES:
                            raise SteamUnavailableError(f"Steam API unavailable. HTTP {response.status_code}")
                        backoff = self.INITIAL_BACKOFF * (2 ** (retries - 1))
                        logger.warning(
                            f"Steam API returned {response.status_code}. "
                            f"Retrying in {backoff}s ({retries}/{self.MAX_RETRIES})..."
                        )
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        raise SteamUnavailableError(f"Unexpected HTTP status {response.status_code}")

                except httpx.RequestError as e:
                    retries += 1
                    if retries > self.MAX_RETRIES:
                        raise SteamUnavailableError(f"Network error after {retries} retries: {e}") from e
                    backoff = self.INITIAL_BACKOFF * (2 ** (retries - 1))
                    logger.warning(f"Network error: {e}. Retrying in {backoff}s ({retries}/{self.MAX_RETRIES})...")
                    await asyncio.sleep(backoff)

            raise SteamUnavailableError(f"Failed to fetch reviews for {app_id} after {self.MAX_RETRIES} retries.")
