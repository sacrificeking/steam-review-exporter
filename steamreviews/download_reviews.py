"""
Steam Review Download Library

This module provides functions to download Steam reviews for given AppIDs.
It handles API rate limits, pagination, and data storage.

Output:
  - reviews are saved as JSON files in a data/ directory.
"""

import copy
import datetime
import json
import logging
import os
import pathlib
import time
from http import HTTPStatus
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Union, cast

import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

DATA_DIR_ENV_VAR = "STEAM_REVIEWS_DATA_DIR"


def parse_app_id(app_id: Union[str, int]) -> Optional[int]:
    """
    Parses an AppID into an integer.

    Args:
        app_id: The Steam AppID (can be string or int).

    Returns:
        The AppID as an integer, or None if parsing fails.
    """
    try:
        return int(str(app_id).strip())
    except ValueError:
        return None


def get_input_app_ids_filename() -> str:
    """Returns the filename where input AppIDs are stored."""
    return "idlist.txt"


def app_id_reader(filename: Optional[str] = None) -> Generator[Optional[int], None, None]:
    """
    Generator that reads AppIDs from a file.

    Args:
        filename: Path to the file containing AppIDs (one per line).
                  If None, uses the default filename.
    """
    if filename is None:
        filename = get_input_app_ids_filename()

    with Path(filename).open(encoding="utf8") as f:
        for row in f:
            yield parse_app_id(row)


def get_processed_app_ids_filename(filename_root: str = "idprocessed") -> str:
    """Returns the filename where processed AppIDs are saved (includes current date)."""
    current_date = time.strftime("%Y%m%d")
    return filename_root + "_on_" + current_date + ".txt"


def get_processed_app_ids() -> Set[int]:
    """Returns a set of all previously processed AppIDs to allow resuming."""
    processed_app_ids_filename = get_processed_app_ids_filename()

    all_app_ids = set()
    try:
        for app_id in app_id_reader(processed_app_ids_filename):
            if app_id is not None:
                all_app_ids.add(app_id)
    except FileNotFoundError:
        logger.info("Creating " + processed_app_ids_filename)
        pathlib.Path(processed_app_ids_filename).touch()
    return all_app_ids


def get_default_review_type() -> str:
    """Returns the default review type ('all')."""
    return "all"


def get_default_request_parameters(chosen_request_params: Optional[Dict] = None) -> Dict[str, str]:
    """
    Returns a dictionary of default parameters for a Steam API request.

    Returns a dictionary of default parameters for a Steam API request.
    """
    default_request_parameters = {
        "json": "1",
        "language": "all",  # API language code e.g. english or german
        "filter": "recent",  # 'recent' or 'updated' needed for 'start_offset' pagination
        "review_type": "all",  # e.g. positive or negative
        "purchase_type": "all",  # e.g. steam or non_steam_purchase
        "num_per_page": "100",  # default is 20, maximum is 100
    }

    if chosen_request_params is not None:
        for element in chosen_request_params:
            default_request_parameters[element] = chosen_request_params[element]

    return default_request_parameters


def get_data_path(data_dir: Optional[Union[str, Path]] = None) -> str:
    """Returns the path to the 'data/' directory where reviews are cached locally."""
    if data_dir is None:
        data_dir = os.environ.get(DATA_DIR_ENV_VAR, "data")

    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    return str(data_path)


def get_steam_api_url() -> str:
    """Returns the URL of the Steam Reviews API."""
    return "https://store.steampowered.com/appreviews/"


def get_steam_api_headers() -> Dict[str, str]:
    """Returns headers sent to the Steam Reviews API."""
    return {"User-Agent": "steam-review-exporter/1.0"}


def get_steam_api_request_timeout() -> Tuple[int, int]:
    """Returns connect and read timeouts for Steam API requests."""
    return (5, 30)


def get_steam_api_rate_limits() -> Dict[str, int]:
    """Returns the rate limits of the Steam API."""
    return {
        "max_num_queries": 150,
        "cooldown": (5 * 60) + 10,  # 5 minutes plus a cushion
        "cooldown_bad_gateway": 10,  # wait time for 502 Bad Gateway
    }


def get_retry_status_codes() -> Set[int]:
    """Returns HTTP status codes that are likely to succeed after a short retry."""
    return {
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    }


def get_output_filename(app_id: int, data_dir: Optional[Union[str, Path]] = None) -> str:
    """Returns the JSON filename for a specific AppID."""
    return str(Path(get_data_path(data_dir)) / f"review_{app_id}.json")


def get_dummy_query_summary() -> Dict[str, int]:
    """Returns a dummy query summary for failed requests."""
    query_summary = {}
    query_summary["total_reviews"] = -1
    return query_summary


def get_empty_review_dict() -> Dict[str, Any]:
    """Returns the default local review cache structure."""
    return {
        "reviews": {},
        "query_summary": get_dummy_query_summary(),
        "cursors": {},
    }


def load_review_dict(app_id: int, data_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Loads existing reviews for an AppID from the local JSON cache.
    Returns an empty structure if no file exists.
    """
    review_data_filename = get_output_filename(app_id, data_dir)

    try:
        with Path(review_data_filename).open(encoding="utf8") as in_json_file:
            review_dict = json.load(in_json_file)

        # Compatibility with data downloaded with previous versions of steamreviews:
        if "cursors" not in review_dict:
            review_dict["cursors"] = {}
    except FileNotFoundError:
        review_dict = get_empty_review_dict()
    except json.JSONDecodeError as error:
        logger.error(f"Could not parse cached review file '{review_data_filename}': {error}")
        review_dict = get_empty_review_dict()

    return cast(Dict[str, Any], review_dict)


def write_review_dict(app_id: int, review_dict: Dict[str, Any], data_dir: Optional[Union[str, Path]] = None) -> None:
    """Writes cached review data atomically."""
    output_path = Path(get_output_filename(app_id, data_dir))
    temp_path = output_path.with_name(output_path.name + ".tmp")
    temp_path.write_text(json.dumps(review_dict) + "\n", encoding="utf8")
    temp_path.replace(output_path)


def get_request(app_id: int, chosen_request_params: Optional[Dict] = None) -> Dict[str, str]:
    """Prepares the request parameters for the API call."""
    request = dict(get_default_request_parameters(chosen_request_params))
    request["appids"] = str(app_id)
    return request


def download_the_full_query_summary(
    app_id: int,
    query_count: int,
    chosen_request_params: Dict,
    override_total_reviews: bool = True,
) -> Tuple[bool, Dict, int]:
    """
    Downloads the full query summary to get correct total review counts.

    Steam API sometimes returns incorrect 'total_reviews' if filters are strict.
    This function forces a broad query to get the true total count.
    """
    try:
        original_review_type = chosen_request_params["review_type"]
    except KeyError:
        original_review_type = None

    # Override the filtering by review type to get all reviews first
    overridden_params = copy.deepcopy(chosen_request_params)
    overridden_params["review_type"] = get_default_review_type()

    (
        success_flag,
        downloaded_reviews,
        query_summary,
        query_count,
        next_cursor,
    ) = download_reviews_for_app_id_with_offset(
        app_id,
        query_count,
        chosen_request_params=overridden_params,
    )

    if (
        override_total_reviews
        and original_review_type is not None
        and original_review_type != get_default_review_type()
    ):
        # Override the total number of reviews with the total number of reviews of the chosen type:
        total_str = "total_" + original_review_type
        if total_str in query_summary:
            query_summary["total_reviews"] = query_summary[total_str]
        else:
            logger.warning(f"Steam API query summary did not include '{total_str}' for appID = {app_id}")

    return success_flag, query_summary, query_count


def download_reviews_for_app_id_with_offset(
    app_id: int,
    query_count: int,
    cursor: str = "*",
    chosen_request_params: Optional[Dict] = None,
) -> Tuple[bool, List[Dict], Dict, int, str]:
    """
    Performs a single request to the Steam API using a specific pagination cursor.
    """
    rate_limits = get_steam_api_rate_limits()

    req_data = get_request(app_id, chosen_request_params)
    req_data["cursor"] = str(cursor)

    request_url = get_steam_api_url() + req_data["appids"]
    retry_status_codes = get_retry_status_codes()

    try:
        resp_data = requests.get(
            request_url,
            params=req_data,
            headers=get_steam_api_headers(),
            timeout=get_steam_api_request_timeout(),
        )
        status_code = resp_data.status_code
        query_count += 1
    except requests.exceptions.RequestException as error:
        query_count += 1
        logger.error(f"Steam API request failed for appID = {app_id} and cursor = {cursor}: {error}")
        return False, [], get_dummy_query_summary(), query_count, cursor

    # Handle temporary Steam API failures.
    while (status_code in retry_status_codes) and (query_count < rate_limits["max_num_queries"]):
        cooldown_duration_for_bad_gateway = rate_limits["cooldown_bad_gateway"]
        logger.warning(
            f"Unexpected status code {resp_data.status_code}. "
            f"cursor = {cursor}. Cooldown: {cooldown_duration_for_bad_gateway} seconds",
        )
        for _ in tqdm(range(cooldown_duration_for_bad_gateway), desc="Bad Gateway Cooldown"):
            time.sleep(1)

        try:
            resp_data = requests.get(
                request_url,
                params=req_data,
                headers=get_steam_api_headers(),
                timeout=get_steam_api_request_timeout(),
            )
            status_code = resp_data.status_code
            query_count += 1
        except requests.exceptions.RequestException as error:
            query_count += 1
            logger.error(f"Steam API retry failed for appID = {app_id} and cursor = {cursor}: {error}")
            return False, [], get_dummy_query_summary(), query_count, cursor

    if status_code == HTTPStatus.OK:
        try:
            result = resp_data.json()
        except ValueError as error:
            result = {"success": 0}
            logger.error(f"Invalid JSON response for appID = {app_id} and cursor = {cursor}: {error}")
    else:
        result = {"success": 0}
        logger.error(
            f"Faulty response status code = {status_code} for appID = {app_id} and cursor = {cursor}",
        )

    success_flag = bool(result.get("success") == 1)

    try:
        downloaded_reviews = result["reviews"]
        query_summary = result["query_summary"]
        next_cursor = result["cursor"]
    except KeyError:
        success_flag = False
        downloaded_reviews = []
        query_summary = get_dummy_query_summary()
        next_cursor = cursor

    return success_flag, downloaded_reviews, query_summary, query_count, next_cursor


def download_reviews_for_app_id(
    app_id: int,
    query_count: int = 0,
    chosen_request_params: Optional[Dict] = None,
    start_cursor: str = "*",
    verbose: bool = False,
    data_dir: Optional[Union[str, Path]] = None,
) -> Tuple[Dict, int]:
    """
    Main loop to download ALL reviews for a given AppID.

    It handles:
    1. Pagination (using 'cursor' to get the next batch).
    2. Rate Limiting (pausing if too many requests).
    3. Updating local cache (appending new reviews).
    """
    rate_limits = get_steam_api_rate_limits()

    request = dict(get_default_request_parameters(chosen_request_params))

    # Check if we need to filter by day range locally (optimistic early exit)
    check_review_timestamp = bool(
        "day_range" in request and request["filter"] != "all",
    )
    if check_review_timestamp:
        current_date = datetime.datetime.now(tz=datetime.UTC)
        num_days = int(request["day_range"])
        date_threshold = current_date - datetime.timedelta(days=num_days)
        timestamp_threshold = datetime.datetime.timestamp(date_threshold)
        if verbose:
            if request["filter"] == "updated":
                collection_keyword = "edited"
            else:
                collection_keyword = "first posted"
            logger.debug(
                f"Collecting reviews {collection_keyword} after {date_threshold}",
            )

    review_dict = load_review_dict(app_id, data_dir)

    previous_review_ids = set(review_dict["reviews"])

    num_reviews = None

    offset = 0
    cursor = start_cursor
    new_reviews: List[Dict] = []
    new_review_ids: Set[int] = set()

    pbar = None

    try:
        # Loop until all reviews are downloaded
        while (num_reviews is None) or (offset < num_reviews):
            if verbose:
                logger.debug(f"Cursor: {cursor}")

            (
                success_flag,
                downloaded_reviews,
                query_summary,
                query_count,
                cursor,
            ) = download_reviews_for_app_id_with_offset(
                app_id,
                query_count,
                cursor,
                chosen_request_params,
            )

            delta_reviews = len(downloaded_reviews)

            # Initialize progress bar once we know the total reviews
            total_reviews = query_summary.get("total_reviews")
            if success_flag and num_reviews is None and total_reviews is not None and total_reviews >= 0:
                review_dict["query_summary"] = query_summary
                num_reviews = total_reviews
                logger.info(f"[appID = {app_id}] expected #reviews = {num_reviews}")
                pbar = tqdm(total=num_reviews, desc=f"Downloading reviews for AppID {app_id}", unit="reviews")

            if pbar:
                pbar.update(delta_reviews)

            offset += delta_reviews

            if success_flag and delta_reviews > 0:
                if check_review_timestamp:
                    if request["filter"] == "updated":
                        timestamp_str_field = "timestamp_updated"
                    else:
                        timestamp_str_field = "timestamp_created"

                    checked_reviews = list(
                        filter(
                            lambda x: x[timestamp_str_field] > timestamp_threshold,
                            downloaded_reviews,
                        ),
                    )

                    delta_checked_reviews = len(checked_reviews)

                    if delta_checked_reviews == 0:
                        if verbose:
                            logger.info(
                                "Exiting the loop to query Steam API, because the timestamp threshold was reached.",
                            )
                        break

                    downloaded_reviews = checked_reviews

                new_reviews.extend(downloaded_reviews)

                downloaded_review_ids = [review["recommendationid"] for review in downloaded_reviews]

                # Detect full redundancy in the latest downloaded reviews
                # This suggests we hit the end of new content, or the API is looping.
                if new_review_ids.issuperset(downloaded_review_ids):
                    if verbose:
                        logger.info(
                            "Exiting the loop to query Steam API, "
                            "because this request only returned redundant reviews.",
                        )
                    break

                new_review_ids = new_review_ids.union(downloaded_review_ids)

            else:
                if verbose:
                    logger.error(
                        "Exiting the loop to query Steam API, because this request failed.",
                    )
                break

            # If we don't know the total yet, fetch full summary
            if num_reviews is None:
                if "total_reviews" not in query_summary:
                    (
                        success_flag,
                        query_summary,
                        query_count,
                    ) = download_the_full_query_summary(
                        app_id,
                        query_count,
                        chosen_request_params or {},
                    )

                review_dict["query_summary"] = query_summary
                num_reviews = query_summary["total_reviews"]
                logger.info(f"[appID = {app_id}] expected #reviews = {num_reviews}")

            # Rate Limit Cooldown
            if query_count >= rate_limits["max_num_queries"]:
                cooldown_duration = rate_limits["cooldown"]
                logger.warning(
                    f"Number of queries {query_count} reached. Cooldown: {cooldown_duration} seconds",
                )
                for _ in tqdm(range(cooldown_duration), desc="Rate Limit Cooldown"):
                    time.sleep(1)
                query_count = 0

            # Optimistic exit check (if we find reviews we already have)
            if not previous_review_ids.isdisjoint(downloaded_review_ids):
                if verbose:
                    logger.warning(
                        "Found existing reviews in this batch. Continuing...",
                    )
                # break  <-- Disabled to allow deep scraping/resuming
    except KeyboardInterrupt:
        logger.warning("\n\n[!] Download cancelled by user. Saving partial data...")
        if pbar:
            pbar.close()
            pbar = None

    # Keep track of the cursor
    review_dict["cursors"][str(cursor)] = time.asctime()

    for review in new_reviews:
        review_id = review["recommendationid"]
        if review_id not in previous_review_ids:
            review_dict["reviews"][review_id] = review

    write_review_dict(app_id, review_dict, data_dir)

    if pbar:
        pbar.close()

    return review_dict, query_count


def download_reviews_for_app_id_batch(
    input_app_ids: Optional[List[int]] = None,
    previously_processed_app_ids: Optional[Set[int]] = None,
    chosen_request_params: Optional[Dict] = None,
    verbose: bool = False,
    data_dir: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Downloads reviews for a list of AppIDs.

    Process:
    1. Loads the list of AppIDs (from file or argument).
    2. Skips AppIDs that are already in the 'processed' list.
    3. Downloads reviews for each AppID sequentially.
    4. Updates the 'processed' list after each successful download.
    """
    if input_app_ids is None:
        logger.info(f"Loading {get_input_app_ids_filename()}")
        # Filter out None values to satisfy List[int] requirement
        input_app_ids = [aid for aid in app_id_reader() if aid is not None]

    if previously_processed_app_ids is None:
        logger.info(f"Loading {get_processed_app_ids_filename()}")
        previously_processed_app_ids = get_processed_app_ids()

    query_count = 0
    game_count = 0
    all_downloads_succeeded = True

    for app_id in input_app_ids:
        if app_id in previously_processed_app_ids:
            logger.info(f"Skipping previously found appID = {app_id}")
            continue

        logger.info(f"Downloading reviews for appID = {app_id}")

        review_dict, query_count = download_reviews_for_app_id(
            app_id,
            query_count,
            chosen_request_params,
            data_dir=data_dir,
            verbose=verbose,
        )

        num_expected_reviews = review_dict["query_summary"]["total_reviews"]
        if num_expected_reviews < 0:
            all_downloads_succeeded = False
            logger.error(f"Skipping processed marker for appID = {app_id}, because the download did not succeed.")
            continue

        game_count += 1

        with Path(get_processed_app_ids_filename()).open("a", encoding="utf8") as f:
            f.write(str(app_id) + "\n")

        num_downloaded_reviews = len(review_dict["reviews"])

        logger.info(
            f"[appID = {app_id}] num_reviews = {num_downloaded_reviews} (expected: {num_expected_reviews})",
        )

    logger.info(f"Game records written: {game_count}")

    return all_downloads_succeeded


if __name__ == "__main__":
    download_reviews_for_app_id_batch(
        input_app_ids=None,
        previously_processed_app_ids=None,
        verbose=False,
    )
