from steamreviews.models import ReviewExportConfig
import pytest


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


if __name__ == "__main__":
    # fast manual check
    test_valid_config()
    test_language_normalization()
    print("Model tests passed!")
