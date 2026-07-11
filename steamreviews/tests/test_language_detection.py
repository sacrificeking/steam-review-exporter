import pytest

from steamreviews.export import filter_reviews_by_language
from steamreviews.language_detection import detect_review_language, iso_matches_target


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("This is a great game with lots of content and fun mechanics.", "en"),
        ("Dies ist ein wunderbares Spiel mit viel Inhalt und Spaß.", "de"),
        ("C'est un jeu fantastique avec beaucoup de contenu intéressant.", "fr"),
        ("Este es un juego fantástico con mucho contenido interesante.", "es"),
    ],
)
def test_detect_review_language_recognizes_common_steam_languages(text: str, expected: str):
    assert detect_review_language(text) == expected


def test_iso_matches_target_accepts_chinese_variants():
    assert iso_matches_target("zh", "zh-cn") is True
    assert iso_matches_target("zh", "zh-tw") is True
    assert iso_matches_target("en", "de") is False


def test_detect_review_language_distinguishes_german_and_english_reviews():
    assert detect_review_language("Dies ist ein ausführlicher deutscher Review Text.") == "de"
    assert detect_review_language("This is clearly an English review with enough length.") == "en"


def test_filter_reviews_by_language_removes_obvious_mismatches():
    reviews = [
        {"review": "Dies ist ein klar deutscher Review mit genug Text.", "language": "german"},
        {
            "review": "This is clearly an English review that should not pass the German filter.",
            "language": "german",
        },
    ]

    filtered = list(filter_reviews_by_language(reviews, "german"))

    assert len(filtered) == 1
    assert "deutsch" in filtered[0]["review"].lower()


def test_filter_reviews_by_language_keeps_short_reviews_without_detection():
    reviews = [{"review": "kurz", "language": "german"}]

    filtered = list(filter_reviews_by_language(reviews, "german"))

    assert filtered == reviews
