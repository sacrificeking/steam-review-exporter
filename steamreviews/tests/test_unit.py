import pathlib
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import steamreviews
import steamreviews.download_reviews as download_reviews


class TestSteamReviewsUnit(unittest.TestCase):
    def test_load_review_dict_defaults(self):
        # Mocking file open to simulate file not found (clean state)
        with patch("pathlib.Path.open", side_effect=FileNotFoundError):
            review_dict = steamreviews.load_review_dict(12345)
            self.assertIn("reviews", review_dict)
            self.assertIn("query_summary", review_dict)
            self.assertEqual(review_dict["query_summary"]["total_reviews"], -1)

    def test_write_and_load_review_dict_with_custom_data_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            review_dict = {
                "reviews": {"1": {"recommendationid": "1", "review": "Nice"}},
                "query_summary": {"total_reviews": 1},
                "cursors": {"*": "now"},
            }

            download_reviews.write_review_dict(12345, review_dict, data_dir=temp_dir)
            loaded = steamreviews.load_review_dict(12345, data_dir=temp_dir)

            self.assertEqual(loaded, review_dict)
            self.assertTrue(pathlib.Path(temp_dir, "review_12345.json").exists())
            self.assertFalse(pathlib.Path(temp_dir, "review_12345.json.tmp").exists())

    def test_load_review_dict_handles_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pathlib.Path(temp_dir, "review_12345.json").write_text("{invalid json", encoding="utf8")

            review_dict = steamreviews.load_review_dict(12345, data_dir=temp_dir)

            self.assertEqual(review_dict["reviews"], {})
            self.assertEqual(review_dict["query_summary"]["total_reviews"], -1)

    @patch("steamreviews.download_reviews.requests.get")
    def test_download_reviews_mocked(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": 1,
            "query_summary": {"total_reviews": 10},
            "reviews": {},
            "cursor": "new_cursor",
        }
        mock_get.return_value = mock_response

        # We mock file operations to strictly test logic, not disk I/O
        with patch("steamreviews.download_reviews.load_review_dict") as mock_load:
            # Basic mock setup for load_review_dict
            mock_load.return_value = {"reviews": {}, "query_summary": {}, "cursors": {}}

            with patch("builtins.open", unittest.mock.mock_open()):  # Suppress file writing
                app_id = 12345
                review_dict, query_count = steamreviews.download_reviews_for_app_id(app_id, verbose=False)

                self.assertEqual(query_count, 1)  # Should have made 1 call
                mock_get.assert_called()

    @patch("steamreviews.download_reviews.requests.get")
    def test_download_request_uses_timeout_and_headers(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": 1,
            "query_summary": {"total_reviews": 0},
            "reviews": [],
            "cursor": "done",
        }
        mock_get.return_value = mock_response

        success, reviews, query_summary, query_count, cursor = download_reviews.download_reviews_for_app_id_with_offset(
            12345,
            0,
        )

        self.assertTrue(success)
        self.assertEqual(reviews, [])
        self.assertEqual(query_summary["total_reviews"], 0)
        self.assertEqual(query_count, 1)
        self.assertEqual(cursor, "done")
        self.assertEqual(mock_get.call_args.kwargs["timeout"], download_reviews.get_steam_api_request_timeout())
        self.assertEqual(mock_get.call_args.kwargs["headers"], download_reviews.get_steam_api_headers())

    @patch("steamreviews.download_reviews.requests.get")
    def test_download_request_handles_network_errors(self, mock_get):
        mock_get.side_effect = download_reviews.requests.exceptions.Timeout("timed out")

        success, reviews, query_summary, query_count, cursor = download_reviews.download_reviews_for_app_id_with_offset(
            12345,
            0,
        )

        self.assertFalse(success)
        self.assertEqual(reviews, [])
        self.assertEqual(query_summary["total_reviews"], -1)
        self.assertEqual(query_count, 1)
        self.assertEqual(cursor, "*")


if __name__ == "__main__":
    unittest.main()
