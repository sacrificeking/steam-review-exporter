import pytest

from steamreviews.models import ReviewExportConfig


def test_valid_config():
    config = ReviewExportConfig(app_id=588650, language="english", filter_type="all", min_len=0, max_len=None)
    assert config.app_id == 588650
    assert config.language == "english"


def test_invalid_app_id():
    with pytest.raises(ValueError):
        ReviewExportConfig(
            app_id=-1,  # Invalid
            language="english",
        )


def test_language_normalization():
    config = ReviewExportConfig(
        app_id=1,
        language="  GerMan  ",  # Should normalize
    )
    assert config.language == "german"


def test_blank_language_after_strip_is_invalid():
    with pytest.raises(ValueError):
        ReviewExportConfig(
            app_id=1,
            language="  ",
        )


def test_invalid_length_range():
    with pytest.raises(ValueError):
        ReviewExportConfig(
            app_id=1,
            language="english",
            min_len=500,
            max_len=100,
        )


def test_author_model_resilience():
    from steamreviews.models import SteamReviewAuthor

    # Only steamid is required, other fields should default
    author = SteamReviewAuthor(steamid="76561197960287930")
    assert author.steamid == "76561197960287930"
    assert author.num_games_owned is None
    assert author.num_reviews is None
    assert author.playtime_forever == 0
    assert author.playtime_last_two_weeks is None
    assert author.playtime_at_review == 0
    assert author.last_played is None


if __name__ == "__main__":
    # fast manual check
    test_valid_config()
    test_language_normalization()
    print("Model tests passed!")
