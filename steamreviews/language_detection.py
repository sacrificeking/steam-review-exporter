import logging
from collections.abc import Callable
from functools import lru_cache
from typing import TypeAlias

from lingua import Language, LanguageDetectorBuilder
from lingua import LanguageDetector as LinguaDetector

logger = logging.getLogger(__name__)

ReviewLanguageDetector: TypeAlias = Callable[[str], str | None]

STEAM_LANG_TO_ISO: dict[str, str] = {
    "english": "en",
    "german": "de",
    "french": "fr",
    "spanish": "es",
    "italian": "it",
    "russian": "ru",
    "schinese": "zh-cn",
    "tchinese": "zh-tw",
    "japanese": "ja",
    "koreana": "ko",
    "portuguese": "pt",
    "brazilian": "pt",
}

_STEAM_LANG_TO_LINGUA: dict[str, Language] = {
    "english": Language.ENGLISH,
    "german": Language.GERMAN,
    "french": Language.FRENCH,
    "spanish": Language.SPANISH,
    "italian": Language.ITALIAN,
    "russian": Language.RUSSIAN,
    "schinese": Language.CHINESE,
    "tchinese": Language.CHINESE,
    "japanese": Language.JAPANESE,
    "koreana": Language.KOREAN,
    "portuguese": Language.PORTUGUESE,
    "brazilian": Language.PORTUGUESE,
}


@lru_cache(maxsize=1)
def _build_detector() -> LinguaDetector:
    languages = sorted(set(_STEAM_LANG_TO_LINGUA.values()), key=lambda lang: lang.name)
    return LanguageDetectorBuilder.from_languages(*languages).with_low_accuracy_mode().build()


def detect_review_language(text: str) -> str | None:
    """Detect the ISO 639-1 language code for review text."""
    language = _build_detector().detect_language_of(text)
    if language is None:
        return None
    return language.iso_code_639_1.name.lower()


def iso_matches_target(detected_iso: str, target_iso: str) -> bool:
    """Return True when detected language matches the requested Steam language."""
    return detected_iso == target_iso or (target_iso.startswith("zh") and detected_iso == "zh")
