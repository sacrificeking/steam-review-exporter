import unittest
import shutil
import pathlib
import steamreviews

# Constants for readability
TEST_APP_ID_1 = 329070  # SpyParty
TEST_APP_ID_2 = 573170  # Another game


class TestSteamReviewsIntegration(unittest.TestCase):
    def tearDown(self):
        # Cleanup: Remove the 'data' directory created during tests
        data_path = pathlib.Path("data")
        if data_path.exists():
            # CAUTION: This recursively deletes the data folder.
            # In a real dev environment, we might want to be more specific
            # (e.g. only delete test-specific IDs), but for this project
            # 'data' is treated as cache.
            shutil.rmtree(data_path, ignore_errors=True)

        # Cleanup: Remove idprocessed files
        for item in pathlib.Path(".").glob("idprocessed*.txt"):
            item.unlink()

    def test_download_reviews_for_app_id(self):
        _, query_count = steamreviews.download_reviews_for_app_id(TEST_APP_ID_2, verbose=True)
        self.assertGreater(query_count, 0)

    def test_download_reviews_batch(self):
        app_ids = [TEST_APP_ID_1, TEST_APP_ID_2]
        steamreviews.download_reviews_for_app_id_batch(app_ids, verbose=True)

        # Verify file creation
        review_dict = steamreviews.load_review_dict(TEST_APP_ID_1)
        self.assertGreater(len(review_dict["reviews"]), 0)

    def test_download_reviews_filtered(self):
        # Integration test for parameters
        request_params = {"language": "english", "review_type": "positive"}
        _, query_count = steamreviews.download_reviews_for_app_id(
            TEST_APP_ID_2,
            chosen_request_params=request_params,
            verbose=True,
        )
        self.assertGreater(query_count, 0)


if __name__ == "__main__":
    unittest.main()
