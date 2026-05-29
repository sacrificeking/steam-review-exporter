from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal


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
        return v.lower().strip()
