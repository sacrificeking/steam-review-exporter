import argparse
import asyncio
import logging
import urllib.parse
from collections.abc import Sequence
from typing import Literal

import httpx
import pydantic

from steamreviews.export import fetch_reviews, process_reviews, save_to_excel
from steamreviews.models import ReviewExportConfig
from steamreviews.utils import setup_logging

logger = logging.getLogger(__name__)

FilterType = Literal["all", "funny", "recent", "updated"]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Download Steam reviews and export them to Excel.")
    parser.add_argument("--app-id", type=int, help="Steam AppID, e.g. 588650 for Dead Cells.")
    parser.add_argument("--language", help="Steam review language, e.g. english, german, or all.")
    parser.add_argument(
        "--filter",
        dest="filter_type",
        choices=["all", "funny", "recent", "updated"],
        default="all",
        help="Steam review sorting/filter mode.",
    )
    parser.add_argument("--min-len", type=int, default=0, help="Minimum review length in characters.")
    parser.add_argument("--max-len", type=int, help="Maximum review length in characters.")
    parser.add_argument("--output-dir", help="Directory where the Excel file should be written.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging.")
    args = parser.parse_args(argv)
    has_cli_config = is_non_interactive_config(args)
    if has_cli_config and (args.app_id is None or args.language is None):
        parser.error("--app-id and --language are required when using command-line options.")
    return args


def is_non_interactive_config(args: argparse.Namespace) -> bool:
    """Return True when command-line options provide an export configuration."""
    return any(
        [
            args.app_id is not None,
            args.language is not None,
            args.filter_type != "all",
            args.min_len != 0,
            args.max_len is not None,
            args.output_dir is not None,
        ]
    )


def search_game_by_name(query: str) -> int | None:
    """
    Queries the Steam Store search API for a game name.
    If multiple matches are found, lists them and prompts the user to select one.
    Returns the resolved AppID, or None if no match was selected/found.
    """
    try:
        url = f"https://store.steampowered.com/api/storesearch/?term={urllib.parse.quote(query)}&l=english&cc=US"
        with httpx.Client(timeout=10) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()

        if not data or not data.get("items"):
            print(f"\nNo games found matching '{query}'.")
            return None

        items = data["items"]
        print(f"\nFound {len(items)} matching games on Steam:")
        for idx, item in enumerate(items, 1):
            name = item.get("name", "Unknown")
            app_id = item.get("id")
            price_info = ""
            if item.get("price"):
                price_val = item["price"].get("final", 0) / 100
                currency = item["price"].get("currency", "USD")
                price_info = f" ({price_val:.2f} {currency})"
            print(f"  [{idx}] {name} (AppID: {app_id}){price_info}")

        print("  [c] Cancel search")

        choice = input(f"\nPlease select a game number (1-{len(items)}) or 'c' to cancel: ").strip().lower()
        if choice == "c" or not choice:
            return None

        if choice.isdigit():
            selected_idx = int(choice) - 1
            if 0 <= selected_idx < len(items):
                return int(items[selected_idx]["id"])

        print("Invalid choice.")
        return None
    except Exception as e:
        logger.warning(f"Error searching for game: {e}")
        return None


def get_app_id() -> int:
    """Queries App-ID or game name from the user."""
    while True:
        app_id_input = input("Please enter the Steam App-ID or game name (e.g. 588650 or 'Dead Cells'):\n").strip()
        if not app_id_input:
            continue

        if app_id_input.isdigit():
            return int(app_id_input)

        # Treat as search query
        app_id = search_game_by_name(app_id_input)
        if app_id is not None:
            return app_id


def get_processing_params() -> tuple[str, FilterType, int, int | None]:
    """Queries processing parameters from the user."""
    language = input("Which language should the reviews be? (e.g. english or german):\n").strip().lower()

    print("\nHow should reviews be filtered?")
    print("  [1] All (default, sorted by helpfulness)")
    print("  [2] Funny (sorted by funny votes)")
    print("  [3] Recent (sorted by creation date)")
    print("  [4] Updated (sorted by update date)")

    filter_choice = input("Enter number (1-4) or press Enter for default: ").strip()

    filter_map: dict[str, FilterType] = {"1": "all", "2": "funny", "3": "recent", "4": "updated"}
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
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        with httpx.Client(timeout=10) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()

        if data and str(app_id) in data:
            success = data[str(app_id)].get("success", False)
            if success:
                return str(data[str(app_id)]["data"]["name"])
    except (KeyError, TypeError, ValueError, httpx.RequestError) as e:
        logger.warning(f"Warning: Could not fetch game name: {e}")

    return str(app_id)


def get_optional_int_input(prompt: str, default_value: int | None = None) -> int | None:
    """Helper to get an optional integer input."""
    user_input = input(prompt).strip()
    if not user_input:
        return default_value
    if user_input.isdigit():
        return int(user_input)
    print(f"Invalid input. Using default: {default_value}")
    return default_value


def get_validated_config(args: argparse.Namespace | None = None) -> ReviewExportConfig:
    """Queries user and returns a validated configuration object."""
    if args is not None and args.app_id is not None and args.language is not None:
        app_id = args.app_id
        language = args.language
        filter_type = args.filter_type
        min_len = args.min_len
        max_len = args.max_len
        output_dir = args.output_dir
    else:
        app_id = get_app_id()
        language, filter_type, min_len, max_len = get_processing_params()
        output_dir = None

    try:
        config = ReviewExportConfig(
            app_id=app_id,
            language=language,
            filter_type=filter_type,
            min_len=min_len,
            max_len=max_len,
            output_dir=output_dir,
        )
        return config
    except pydantic.ValidationError as e:
        logger.error(f"Configuration Error: {e}")
        raise


async def export_once(config: ReviewExportConfig) -> bool:
    game_name = await asyncio.to_thread(get_game_name, config.app_id)

    logger.info(f"Starting review export for App ID {config.app_id} ({game_name})...")

    # We use SQLite storage for the CLI implementation
    reviews = await fetch_reviews(
        config.app_id, config.language, config.filter_type, config.min_len, config.max_len, config.output_dir
    )

    if not reviews:
        logger.warning(f"No reviews found for '{game_name}' (AppID {config.app_id}).")
        logger.info("Check if the AppID is correct.")
        logger.info("Check if the game has reviews in the selected language.")
        return False

    logger.info("Downloaded reviews. Processing data...")
    try:
        df = await asyncio.to_thread(process_reviews, reviews, config.app_id)
    except ValueError as e:
        logger.error(str(e))
        return False
    return save_to_excel(
        df,
        config.app_id,
        game_name,
        config.language,
        config.filter_type,
        config.min_len,
        config.max_len,
        config.output_dir,
    )


def get_next_config(config: ReviewExportConfig) -> ReviewExportConfig | None:
    """Prompts for the next interactive AppID while keeping the existing processing parameters."""
    again = input("\nDo you want to download another game with the same parameters? (y/n): ").strip().lower()
    if again != "y":
        return None

    new_app_id = get_app_id()
    return ReviewExportConfig(
        app_id=new_app_id,
        language=config.language,
        filter_type=config.filter_type,
        min_len=config.min_len,
        max_len=config.max_len,
        output_dir=config.output_dir,
    )


async def run_cli(args: argparse.Namespace, non_interactive: bool) -> int:
    """Runs the CLI workflow and returns a process-style status code."""
    try:
        config = get_validated_config(args)
        exported_any = False

        while True:
            result = await export_once(config)
            exported_any = result or exported_any

            if non_interactive:
                break

            next_config = get_next_config(config)
            if next_config is None:
                break
            config = next_config

        return 0 if exported_any else 1

    except KeyboardInterrupt:
        logger.warning("\nOperation cancelled by user.")
        return 130
    except EOFError:
        logger.error("\nInput stream closed unexpectedly. Exiting.")
        return 1
    except pydantic.ValidationError:
        return 2
    except Exception as e:
        logger.critical(f"\nAn unexpected error occurred: {e}")
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    non_interactive = is_non_interactive_config(args)
    setup_logging(verbose=args.verbose)
    return asyncio.run(run_cli(args, non_interactive))


if __name__ == "__main__":
    raise SystemExit(main())
