import unittest
from unittest.mock import patch, MagicMock
import steamreviews


class TestSteamReviewsUnit(unittest.TestCase):
    def test_load_review_dict_defaults(self):
        # Mocking file open to simulate file not found (clean state)
        with patch("pathlib.Path.open", side_effect=FileNotFoundError):
            review_dict = steamreviews.load_review_dict(12345)
            self.assertIn("reviews", review_dict)
            self.assertIn("query_summary", review_dict)
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


if __name__ == "__main__":
    unittest.main()
