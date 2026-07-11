import httpx
import pytest

from steamreviews.api import (
    SteamAPIClient,
    SteamAPIError,
    SteamRateLimitError,
    SteamUnavailableError,
    SteamValidationError,
)


def _steam_response_payload() -> dict:
    return {
        "success": 1,
        "query_summary": {"total_reviews": 10},
        "reviews": [
            {
                "recommendationid": "1",
                "review": "nice",
                "author": {
                    "steamid": "123",
                    "num_games_owned": 1,
                    "num_reviews": 1,
                    "playtime_forever": 1,
                    "playtime_last_two_weeks": 1,
                    "playtime_at_review": 1,
                    "last_played": 1,
                },
                "language": "english",
                "timestamp_created": 1,
                "timestamp_updated": 1,
                "voted_up": True,
                "votes_up": 1,
                "votes_funny": 1,
                "weighted_vote_score": "0",
                "comment_count": 0,
                "steam_purchase": True,
                "received_for_free": False,
                "written_during_early_access": False,
            }
        ],
        "cursor": "next",
    }


@pytest.mark.asyncio
async def test_get_reviews_validation_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"invalid": "data"}))

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SteamAPIClient(http_client=http_client)
        with pytest.raises(SteamValidationError):
            await client.get_reviews(123, "*", {})


@pytest.mark.asyncio
async def test_get_reviews_rate_limit_raise():
    transport = httpx.MockTransport(lambda request: httpx.Response(429))

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SteamAPIClient(raise_on_rate_limit=True, http_client=http_client)
        with pytest.raises(SteamRateLimitError):
            await client.get_reviews(123, "*", {})


@pytest.mark.asyncio
async def test_get_reviews_unavailable_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(500))

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SteamAPIClient(http_client=http_client)
        client.INITIAL_BACKOFF = 0.01  # speed up test
        with pytest.raises(SteamUnavailableError):
            await client.get_reviews(123, "*", {})


def test_package_user_agent_includes_version():
    from steamreviews.api import _package_user_agent

    assert _package_user_agent().startswith("steam-review-exporter/")


@pytest.mark.asyncio
async def test_api_client_sends_versioned_user_agent():
    captured_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(dict(request.headers))
        return httpx.Response(200, json=_steam_response_payload())

    transport = httpx.MockTransport(handler)

    async with SteamAPIClient() as client:
        client._client = httpx.AsyncClient(transport=transport, headers=client.headers)
        client._owns_client = True
        await client.get_reviews(123, "*", {})

    assert captured_headers.get("user-agent", "").startswith("steam-review-exporter/")


@pytest.mark.asyncio
async def test_api_client_accepts_numeric_recommendationid():
    payload = _steam_response_payload()
    payload["reviews"][0]["recommendationid"] = 99999
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SteamAPIClient(http_client=http_client)
        response = await client.get_reviews(123, "*", {})

    assert response.reviews[0].recommendationid == "99999"


@pytest.mark.asyncio
async def test_api_client_success():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=_steam_response_payload()))

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SteamAPIClient(http_client=http_client)
        response = await client.get_reviews(123, "*", {})

    assert response is not None
    assert response.success == 1
    assert len(response.reviews) == 1


@pytest.mark.asyncio
async def test_api_client_retries_on_500():
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SteamAPIClient(http_client=http_client)
        client.MAX_RETRIES = 2
        client.INITIAL_BACKOFF = 0.01
        with pytest.raises(SteamAPIError):
            await client.get_reviews(123, "*", {})

    assert request_count == 3  # Initial + 2 retries


@pytest.mark.asyncio
async def test_api_client_reuses_one_http_client_in_context(monkeypatch):
    created_clients = []

    class FakeResponse:
        status_code = 200

        def json(self) -> dict:
            return {"success": 1, "reviews": [], "cursor": "next"}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            self.is_closed = False
            self.cursors = []
            created_clients.append(self)

        async def get(self, url: str, params: dict[str, str]) -> FakeResponse:
            self.cursors.append(params["cursor"])
            return FakeResponse()

        async def aclose(self) -> None:
            self.is_closed = True

    monkeypatch.setattr("steamreviews.api.httpx.AsyncClient", FakeAsyncClient)

    async with SteamAPIClient() as client:
        await client.get_reviews(123, "*", {})
        await client.get_reviews(123, "next", {})

    assert len(created_clients) == 1
    assert created_clients[0].cursors == ["*", "next"]
    assert created_clients[0].is_closed is True


@pytest.mark.vcr
@pytest.mark.asyncio
async def test_api_client_vcr_snapshot():
    """
    Validates the actual Steam API structure using vcrpy.
    This test will record the HTTP response on the first run and replay it subsequently,
    ensuring we test against real data structures without relying on manual mocks.
    """
    async with SteamAPIClient() as client:
        response = await client.get_reviews(588650, "*", {"json": "1", "num_per_page": "10"})

    assert response is not None
    assert response.success == 1
    assert len(response.reviews) > 0
    assert getattr(response.reviews[0], "recommendationid", None) is not None


@pytest.mark.asyncio
async def test_get_reviews_not_found_error():
    from steamreviews.api import SteamNotFoundError

    transport = httpx.MockTransport(lambda request: httpx.Response(404))

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SteamAPIClient(http_client=http_client)
        with pytest.raises(SteamNotFoundError):
            await client.get_reviews(123, "*", {})


@pytest.mark.asyncio
async def test_get_reviews_other_4xx_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(400))

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SteamAPIClient(http_client=http_client)
        with pytest.raises(SteamValidationError):
            await client.get_reviews(123, "*", {})
