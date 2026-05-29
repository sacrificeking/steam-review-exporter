from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, Self


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
