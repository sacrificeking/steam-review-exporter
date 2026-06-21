import pytest
from unittest.mock import patch, MagicMock
from steamreviews.api import SteamAPIClient, SteamAPIError
import httpx

@pytest.mark.asyncio
async def test_api_client_success():
    client = SteamAPIClient()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": 1,
            "query_summary": {"total_reviews": 10},
            "reviews": [{
                "recommendationid": "1", 
                "review": "nice",
                "author": {"steamid": "123", "num_games_owned": 1, "num_reviews": 1, "playtime_forever": 1, "playtime_last_two_weeks": 1, "playtime_at_review": 1, "last_played": 1},
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
                "written_during_early_access": False
            }],
            "cursor": "next"
        }
        mock_get.return_value = mock_resp
        
        response = await client.get_reviews(123, "*", {})
        
        assert response is not None
        assert response.success == 1
        assert len(response.reviews) == 1

@pytest.mark.asyncio
async def test_api_client_retries_on_500(monkeypatch):
    client = SteamAPIClient()
    client.MAX_RETRIES = 2
    client.INITIAL_BACKOFF = 0.01
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp
        
        with pytest.raises(SteamAPIError):
            await client.get_reviews(123, "*", {})
        
        assert mock_get.call_count == 3  # Initial + 2 retries
