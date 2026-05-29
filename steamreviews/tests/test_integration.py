import pathlib

import pytest

import steamreviews

pytestmark = pytest.mark.integration

TEST_APP_ID_1 = 329070  # SpyParty
TEST_APP_ID_2 = 573170


def test_download_reviews_for_app_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    _, query_count = steamreviews.download_reviews_for_app_id(TEST_APP_ID_2, verbose=True)

    assert query_count > 0


def test_download_reviews_batch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    app_ids = [TEST_APP_ID_1, TEST_APP_ID_2]
    steamreviews.download_reviews_for_app_id_batch(app_ids, verbose=True)

    review_dict = steamreviews.load_review_dict(TEST_APP_ID_1)
    assert len(review_dict["reviews"]) > 0


def test_download_reviews_filtered(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    request_params = {"language": "english", "review_type": "positive"}
    _, query_count = steamreviews.download_reviews_for_app_id(
        TEST_APP_ID_2,
        chosen_request_params=request_params,
        verbose=True,
    )

    assert query_count > 0
    assert pathlib.Path("data").exists()
