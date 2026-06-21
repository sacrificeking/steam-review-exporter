from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from steamreviews.scraper import SteamCursorLoopError, SteamReviewScraper
from steamreviews.storage import MemoryStorage, NullStorage


@pytest.mark.asyncio
async def test_scraper_fetch_all():
    import shutil
    import tempfile

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
        mock_get.side_effect = [mock_resp, mock_resp2]

        success = await scraper.fetch_all_reviews(123, {"language": "english"})

        assert success is True
        assert scraper.storage.get_review_count(123) == 1
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.mark.asyncio
async def test_fetch_reviews_stream_yields_batches():
    scraper = SteamReviewScraper(storage=NullStorage())
    with patch("steamreviews.api.SteamAPIClient.get_reviews", new_callable=AsyncMock) as mock_get:
        mock_resp1 = MagicMock()
        mock_resp1.query_summary.model_dump.return_value = {"total_reviews": 2}
        mock_resp1.query_summary.total_reviews = 2

        r1 = MagicMock()
        r1.model_dump.return_value = {"id": "1"}
        r2 = MagicMock()
        r2.model_dump.return_value = {"id": "2"}

        mock_resp1.reviews = [r1, r2]
        mock_resp1.cursor = "cursor2"

        mock_resp2 = MagicMock()
        mock_resp2.reviews = []
        mock_resp2.cursor = "cursor2"

        mock_get.side_effect = [mock_resp1, mock_resp2]

        batches = []
        async for batch in scraper.fetch_reviews_stream(123, {}):
            batches.append(batch)

        assert len(batches) == 1
        assert len(batches[0]) == 2
        assert batches[0][0]["id"] == "1"


@pytest.mark.asyncio
async def test_fetch_reviews_stream_loop_protection():
    scraper = SteamReviewScraper(storage=MemoryStorage())
    with patch("steamreviews.api.SteamAPIClient.get_reviews", new_callable=AsyncMock) as mock_get:
        mock_resp1 = MagicMock()
        mock_resp1.query_summary.model_dump.return_value = {"total_reviews": 100}
        mock_resp1.reviews = [MagicMock()]
        mock_resp1.cursor = "cursorA"

        mock_resp2 = MagicMock()
        mock_resp2.query_summary.model_dump.return_value = {"total_reviews": 100}
        mock_resp2.reviews = [MagicMock()]
        mock_resp2.cursor = "cursorB"

        mock_resp3 = MagicMock()
        mock_resp3.query_summary.model_dump.return_value = {"total_reviews": 100}
        mock_resp3.reviews = [MagicMock()]
        mock_resp3.cursor = "cursorA"  # Loop!

        mock_get.side_effect = [mock_resp1, mock_resp2, mock_resp3]

        with pytest.raises(SteamCursorLoopError):
            async for _ in scraper.fetch_reviews_stream(123, {}):
                pass


@pytest.mark.asyncio
async def test_fetch_reviews_stream_exception_passthrough():
    scraper = SteamReviewScraper(storage=MemoryStorage())
    from steamreviews.api import SteamRateLimitError

    with patch("steamreviews.api.SteamAPIClient.get_reviews", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = SteamRateLimitError("Rate limited!")

        with pytest.raises(SteamRateLimitError):
            async for _ in scraper.fetch_reviews_stream(123, {}):
                pass
