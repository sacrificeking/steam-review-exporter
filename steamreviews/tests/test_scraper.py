import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from steamreviews.scraper import SteamReviewScraper

@pytest.mark.asyncio
async def test_scraper_fetch_all():
    import tempfile
    import shutil
    tmp_path = tempfile.mkdtemp()
    scraper = SteamReviewScraper(data_dir=tmp_path)
    
    with patch("steamreviews.api.SteamAPIClient.get_reviews", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.query_summary.model_dump.return_value = {"total_reviews": 1}
        mock_resp.query_summary.total_reviews = 1
        mock_review = MagicMock()
        mock_review.model_dump.return_value = {"recommendationid": "1", "review": "nice"}
        mock_resp.reviews = [mock_review]
        mock_resp.cursor = "next"
        
        mock_resp2 = MagicMock()
        mock_resp2.reviews = []
        mock_resp2.cursor = "next"
        
        mock_get.side_effect = [mock_resp, mock_resp2]
        
        success = await scraper.fetch_all_reviews(123, {"language": "english"})
        
        assert success is True
        assert scraper.cache.get_review_count(123) == 1
    shutil.rmtree(tmp_path, ignore_errors=True)
