import asyncio
import logging
from importlib.metadata import PackageNotFoundError, version
from typing import Self

import httpx
from pydantic import ValidationError

from steamreviews.models import SteamApiResponse

logger = logging.getLogger(__name__)


def _package_user_agent() -> str:
    try:
        pkg_version = version("steam-review-exporter")
    except PackageNotFoundError:
        pkg_version = "unknown"
    return f"steam-review-exporter/{pkg_version}"


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


class SteamNotFoundError(SteamAPIError):
    """Raised when the requested AppID is not found (HTTP 404)."""

    pass


class SteamAPIClient:
    """Async HTTP client for Steam API using httpx."""

    BASE_URL = "https://store.steampowered.com/appreviews/"
    RATE_LIMIT_COOLDOWN = 300  # 5 minutes
    INITIAL_BACKOFF = 2.0
    MAX_RETRIES = 5
    MAX_QUERIES = 150

    def __init__(
        self,
        raise_on_rate_limit: bool = False,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.headers = {"User-Agent": _package_user_agent()}
        self.timeout = httpx.Timeout(5.0, read=30.0)
        self._query_count = 0
        self.raise_on_rate_limit = raise_on_rate_limit
        self._client = http_client
        self._owns_client = http_client is None

    async def __aenter__(self) -> Self:
        self._ensure_client()
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close an internally managed HTTP client."""
        if self._client is not None and self._owns_client and not self._client.is_closed:
            await self._client.aclose()
        if self._owns_client:
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout, headers=self.headers)
            self._owns_client = True
        return self._client

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
        client = self._ensure_client()

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

                elif response.status_code == 404:
                    raise SteamNotFoundError(f"AppID {app_id} not found (HTTP 404)")

                elif 400 <= response.status_code < 500:
                    raise SteamValidationError(f"Client error (HTTP {response.status_code})")

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
