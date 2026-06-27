from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator


class ReviewExportConfig(BaseModel):
    app_id: int = Field(..., gt=0, description="Steam App ID must be a positive integer")
    language: str = Field(..., min_length=2, description="Language code or name")
    filter_type: Literal["all", "funny", "recent", "updated"] = "all"
    min_len: int = Field(0, ge=0, description="Minimum review length")
    max_len: int | None = Field(None, gt=0, description="Maximum review length")
    output_dir: str | None = Field(None, min_length=1, description="Directory for exported Excel files")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        language = v.lower().strip()
        if not language:
            raise ValueError("Language must not be empty")
        return language

    @model_validator(mode="after")
    def validate_length_range(self) -> Self:
        if self.max_len is not None and self.max_len < self.min_len:
            raise ValueError("Maximum review length must be greater than or equal to minimum review length")
        return self


class SteamReviewAuthor(BaseModel):
    steamid: str
    num_games_owned: int | None = None
    num_reviews: int | None = None
    playtime_forever: int = 0
    playtime_last_two_weeks: int | None = None
    playtime_at_review: int = 0
    last_played: int | None = None


class SteamReview(BaseModel):
    recommendationid: str
    author: SteamReviewAuthor
    language: str
    review: str
    timestamp_created: int
    timestamp_updated: int
    voted_up: bool
    votes_up: int
    votes_funny: int
    weighted_vote_score: float = 0.0
    comment_count: int = 0
    steam_purchase: bool = False
    received_for_free: bool = False
    written_during_early_access: bool = False
    hidden_in_steam_china: bool = False
    steam_china_banned: bool = False


class SteamQuerySummary(BaseModel):
    num_reviews: int = 0
    review_score: int = 0
    review_score_desc: str = ""
    total_positive: int = 0
    total_negative: int = 0
    total_reviews: int = 0


class SteamApiResponse(BaseModel):
    success: int
    query_summary: SteamQuerySummary | None = None
    reviews: list[SteamReview] = []
    cursor: str = ""
