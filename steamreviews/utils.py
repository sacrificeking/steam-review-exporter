import logging
from rich.logging import RichHandler


def setup_logging(verbose: bool = False) -> None:
    """
    Configures the root logger to use RichHandler for pretty output.

    Args:
        verbose: If True, set level to DEBUG. Otherwise, INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Configure the root logger
    logging.basicConfig(
        level=level, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True, markup=True)]
    )

    # Suppress noisy libraries if needed (optional)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
