import logging

try:
    from rich.logging import RichHandler
except ImportError:
    RichHandler = None  # type: ignore


def setup_logging(verbose: bool = False) -> None:
    """
    Configures the root logger to use RichHandler for pretty output,
    with a fallback to standard StreamHandler if rich is not installed.

    Args:
        verbose: If True, set level to DEBUG. Otherwise, INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO

    handler: logging.Handler
    if RichHandler is not None:
        handler = RichHandler(rich_tracebacks=True, markup=True)
        log_format = "%(message)s"
    else:
        handler = logging.StreamHandler()
        log_format = "[%(asctime)s] %(levelname)s: %(message)s"

    # Configure the root logger
    logging.basicConfig(level=level, format=log_format, datefmt="[%X]", handlers=[handler])

    # Suppress noisy libraries if needed (optional)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
