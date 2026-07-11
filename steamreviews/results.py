from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FetchOutcome:
    """Result metadata for a Steam review download run."""

    complete: bool
    downloaded_count: int
    expected_total: int | None = None
    failure_reason: str | None = None

    @property
    def partial(self) -> bool:
        return not self.complete and self.downloaded_count > 0


@dataclass(frozen=True)
class FetchReviewsResult:
    """Filtered reviews plus download outcome metadata."""

    reviews: list[dict[str, Any]]
    outcome: FetchOutcome


@dataclass(frozen=True)
class ExportOnceResult:
    """Outcome of a single CLI export run."""

    exported: bool
    partial: bool = False
