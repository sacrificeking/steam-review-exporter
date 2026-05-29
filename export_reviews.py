import requests
import logging
from typing import Tuple, Optional
from steamreviews.utils import setup_logging
from steamreviews.export import fetch_reviews, process_reviews, save_to_excel
from steamreviews.models import ReviewExportConfig
import pydantic

logger = logging.getLogger(__name__)


def get_app_id() -> int:
    """Queries App-ID from the user."""
    app_id_input = input("Please enter the Steam App-ID (e.g. 588650 for Dead Cells):\n").strip()
    while not app_id_input.isdigit():
        app_id_input = input("Invalid input. Please enter a numeric App-ID:\n").strip()
    return int(app_id_input)


def get_processing_params() -> Tuple[str, str, int, Optional[int]]:
    """Queries processing parameters from the user."""
    language = input("Which language should the reviews be? (e.g. english or german):\n").strip().lower()

    print("\nHow should reviews be filtered?")
    print("  [1] All (default, sorted by helpfulness)")
    print("  [2] Funny (sorted by funny votes)")
    print("  [3] Recent (sorted by creation date)")
    print("  [4] Updated (sorted by update date)")

    filter_choice = input("Enter number (1-4) or press Enter for default: ").strip()

    filter_map = {"1": "all", "2": "funny", "3": "recent", "4": "updated"}
    filter_type = filter_map.get(filter_choice, "all")
    print(f"Selected filter: {filter_type}\n")

    # New: Length filtering prompts
    print("Optional: Filter by review length (characters). Press Enter to skip.")
    # min_len defaults to 0, so we can cast to int safely if we trust the logic,
    # but mypy needs help since get_optional_int_input returns Optional[int]
    min_len_val = get_optional_int_input("Minimum length (default 0): ", 0)
    min_len = int(min_len_val) if min_len_val is not None else 0
    max_len = get_optional_int_input("Maximum length (default No Limit): ", None)
    print(f"Length filter: Min={min_len}, Max={max_len if max_len is not None else 'No Limit'}\n")

    return language, filter_type, min_len, max_len


def get_game_name(app_id: int) -> str:
    """Fetches the game name from the Steam Store API."""
    try:
        url = f"http://store.steampowered.com/api/appdetails?appids={app_id}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if data and str(app_id) in data:
            success = data[str(app_id)].get("success", False)
            if success:
                return str(data[str(app_id)]["data"]["name"])
    except Exception as e:
        logger.warning(f"Warning: Could not fetch game name: {e}")

    return str(app_id)


def get_optional_int_input(prompt: str, default_value: Optional[int] = None) -> Optional[int]:
    """Helper to get an optional integer input."""
    user_input = input(prompt).strip()
    if not user_input:
        return default_value
    if user_input.isdigit():
        return int(user_input)
    print(f"Invalid input. Using default: {default_value}")
    return default_value


def get_validated_config() -> ReviewExportConfig:
    """Queries user and returns a validated configuration object."""
    # Initial parameters
    app_id = get_app_id()
    language, filter_type, min_len, max_len = get_processing_params()

    try:
        config = ReviewExportConfig(
            app_id=app_id,
            language=language,
            filter_type=filter_type,  # type: ignore
            min_len=min_len,
            max_len=max_len,
        )
        return config
    except pydantic.ValidationError as e:
        logger.error(f"Configuration Error: {e}")
        raise


def main():
    setup_logging()
    try:
        # Initial parameters
        config = get_validated_config()

        while True:
            game_name = get_game_name(config.app_id)
            logger.info(f"Fetching reviews for '{game_name}' (AppID {config.app_id})...")

            reviews = fetch_reviews(config.app_id, config.language, config.filter_type, config.min_len, config.max_len)

            if reviews:
                logger.info(f"Downloaded {len(reviews)} reviews. Processing data...")
                df = process_reviews(reviews, config.app_id)
                save_to_excel(
                    df, config.app_id, game_name, config.language, config.filter_type, config.min_len, config.max_len
                )
            else:
                logger.warning(f"No reviews found for '{game_name}' (AppID {config.app_id}).")
                logger.info("Check if the AppID is correct.")
                logger.info("Check if the game has reviews in the selected language.")

            # Loop check
            again = input("\nDo you want to download another game with the same parameters? (y/n): ").strip().lower()
            if again != "y":
                break

            # Ask for new AppID (and re-validate)
            # Note: For simplicity in this loop, we just re-ask AppID but keep other params constant,
            # mirroring original behavior, but wrapped in a new config.
            new_app_id = get_app_id()
            config = ReviewExportConfig(
                app_id=new_app_id,
                language=config.language,
                filter_type=config.filter_type,
                min_len=config.min_len,
                max_len=config.max_len,
            )

    except KeyboardInterrupt:
        logger.warning("\nOperation cancelled by user.")
    except EOFError:
        logger.error("\nInput stream closed unexpectedly. Exiting.")
    except Exception as e:
        logger.critical(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
