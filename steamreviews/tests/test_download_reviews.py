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
def test_execute_steam_api_request_uses_timeout_and_headers(mock_get):
    mock_response = MagicMock()
    mock_get.return_value = mock_response

    response = download_reviews.execute_steam_api_request(
        12345,
        "*",
        "https://store.steampowered.com/appreviews/12345",
        {"json": "1", "appids": "12345", "cursor": "*"},
    )

    assert response is mock_response
    assert mock_get.call_args.kwargs["timeout"] == download_reviews.get_steam_api_request_timeout()
    assert mock_get.call_args.kwargs["headers"] == download_reviews.get_steam_api_headers()


@patch("steamreviews.download_reviews.requests.get")
def test_execute_steam_api_request_handles_network_errors(mock_get):
    mock_get.side_effect = download_reviews.requests.exceptions.Timeout("timed out")

    response = download_reviews.execute_steam_api_request(
        12345,
        "*",
        "https://store.steampowered.com/appreviews/12345",
        {"json": "1", "appids": "12345", "cursor": "*"},
    )

    assert response is None


def test_parse_steam_api_response_handles_bad_status():
    mock_response = MagicMock()
    mock_response.status_code = 500

    success, reviews, query_summary, cursor = download_reviews.parse_steam_api_response(12345, "*", mock_response)

    assert success is False
    assert reviews == []
    assert query_summary["total_reviews"] == -1
    assert cursor == "*"


def test_parse_steam_api_response_handles_invalid_json():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("invalid json")

    success, reviews, query_summary, cursor = download_reviews.parse_steam_api_response(12345, "*", mock_response)

    assert success is False
    assert reviews == []
    assert query_summary["total_reviews"] == -1
    assert cursor == "*"


def test_parse_steam_api_payload_rejects_non_object_payload():
    success, reviews, query_summary, cursor = download_reviews.parse_steam_api_payload(12345, "*", [])

    assert success is False
    assert reviews == []
    assert query_summary["total_reviews"] == -1
    assert cursor == "*"


def test_parse_steam_api_payload_rejects_invalid_reviews_shape():
    payload = {"success": 1, "reviews": {}, "query_summary": {"total_reviews": 0}, "cursor": "done"}

    success, reviews, query_summary, cursor = download_reviews.parse_steam_api_payload(12345, "*", payload)

    assert success is False
    assert reviews == []
    assert query_summary["total_reviews"] == -1
    assert cursor == "*"


def test_parse_steam_api_payload_rejects_invalid_query_summary_shape():
    payload = {"success": 1, "reviews": [], "query_summary": [], "cursor": "done"}

    success, reviews, query_summary, cursor = download_reviews.parse_steam_api_payload(12345, "*", payload)

    assert success is False
    assert reviews == []
    assert query_summary["total_reviews"] == -1
    assert cursor == "*"


def test_parse_steam_api_payload_rejects_invalid_cursor_shape():
    payload = {"success": 1, "reviews": [], "query_summary": {"total_reviews": 0}, "cursor": None}

    success, reviews, query_summary, cursor = download_reviews.parse_steam_api_payload(12345, "*", payload)

    assert success is False
    assert reviews == []
    assert query_summary["total_reviews"] == -1
    assert cursor == "*"


def test_parse_steam_api_payload_preserves_missing_success_behavior_for_valid_shape():
    payload = {"reviews": [], "query_summary": {"total_reviews": 0}, "cursor": "done"}

    success, reviews, query_summary, cursor = download_reviews.parse_steam_api_payload(12345, "*", payload)

    assert success is False
    assert reviews == []
    assert query_summary["total_reviews"] == 0
    assert cursor == "done"


def test_build_timestamp_filter_uses_created_or_updated_field():
    recent_filter = download_reviews.build_timestamp_filter({"filter": "recent", "day_range": "7"})
    updated_filter = download_reviews.build_timestamp_filter({"filter": "updated", "day_range": "7"})
    all_filter = download_reviews.build_timestamp_filter({"filter": "all", "day_range": "7"})

    assert recent_filter is not None
    assert recent_filter["field"] == "timestamp_created"
    assert updated_filter is not None
    assert updated_filter["field"] == "timestamp_updated"
    assert all_filter is None


def test_apply_timestamp_filter_keeps_reviews_after_threshold():
    timestamp_filter = {"field": "timestamp_created", "threshold": 100.0}
    reviews = [
        {"recommendationid": "1", "timestamp_created": 99.0},
        {"recommendationid": "2", "timestamp_created": 101.0},
    ]

    assert download_reviews.apply_timestamp_filter(reviews, timestamp_filter) == [reviews[1]]
    assert download_reviews.apply_timestamp_filter(reviews, None) == reviews


def test_is_redundant_batch_detects_only_already_seen_review_ids():
    assert download_reviews.is_redundant_batch({"1", "2"}, ["1", "2"]) is True
    assert download_reviews.is_redundant_batch({"1"}, ["1", "2"]) is False


def test_merge_new_reviews_preserves_existing_reviews():
    review_dict = {"reviews": {"1": {"recommendationid": "1", "review": "old"}}}
    new_reviews = [
        {"recommendationid": "1", "review": "new"},
        {"recommendationid": "2", "review": "fresh"},
    ]

    download_reviews.merge_new_reviews(review_dict, new_reviews, {"1"})

    assert review_dict["reviews"]["1"]["review"] == "old"
    assert review_dict["reviews"]["2"]["review"] == "fresh"


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
