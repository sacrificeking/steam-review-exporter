from unittest.mock import MagicMock, patch

import steamreviews
import steamreviews.download_reviews as download_reviews


@patch("steamreviews.download_reviews.download_reviews_for_app_id_with_offset")
def test_download_reviews_persists_query_summary(mock_download, tmp_path):
    mock_download.return_value = (
        True,
        [],
        {"total_reviews": 0},
        1,
        "done",
    )

    review_dict, query_count = steamreviews.download_reviews_for_app_id(12345, data_dir=tmp_path)

    assert query_count == 1
    assert review_dict["query_summary"]["total_reviews"] == 0

    loaded = steamreviews.load_review_dict(12345, data_dir=tmp_path)
    assert loaded["query_summary"]["total_reviews"] == 0


@patch("steamreviews.download_reviews.requests.get")
def test_download_request_handles_missing_success_field(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "query_summary": {"total_reviews": 0},
        "reviews": [],
        "cursor": "done",
    }
    mock_get.return_value = mock_response

    success, reviews, query_summary, query_count, cursor = download_reviews.download_reviews_for_app_id_with_offset(
        12345,
        0,
    )

    assert success is False
    assert reviews == []
    assert query_summary["total_reviews"] == 0
    assert query_count == 1
    assert cursor == "done"


@patch("steamreviews.download_reviews.download_reviews_for_app_id")
def test_batch_does_not_mark_failed_download_as_processed(mock_download, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_download.return_value = (
        {
            "reviews": {},
            "query_summary": {"total_reviews": -1},
            "cursors": {},
        },
        1,
    )

    result = steamreviews.download_reviews_for_app_id_batch(
        input_app_ids=[12345],
        previously_processed_app_ids=set(),
    )

    assert result is False
    assert not list(tmp_path.glob("idprocessed*.txt"))
