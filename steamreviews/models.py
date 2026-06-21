from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, Self, Any, Dict, List


class ReviewExportConfig(BaseModel):
    app_id: int = Field(..., gt=0, description="Steam App ID must be a positive integer")
    language: str = Field(..., min_length=2, description="Language code or name")
    filter_type: Literal["all", "funny", "recent", "updated"] = "all"
    min_len: int = Field(0, ge=0, description="Minimum review length")
    max_len: Optional[int] = Field(None, gt=0, description="Maximum review length")
    output_dir: Optional[str] = Field(None, min_length=1, description="Directory for exported Excel files")

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
    num_games_owned: int = 0
    num_reviews: int = 0
    playtime_forever: int = 0
    playtime_last_two_weeks: int = 0
    playtime_at_review: int = 0
    last_played: int = 0

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
    query_summary: Optional[SteamQuerySummary] = None
    reviews: List[SteamReview] = []
    cursor: str = ""
