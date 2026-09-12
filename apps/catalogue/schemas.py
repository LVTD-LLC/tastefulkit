from ninja import Schema
from pydantic import Field, field_validator

from apps.catalogue.models import Design


class DesignIn(Schema):
    title: str = Field(min_length=2, max_length=160)
    source_url: str = Field(max_length=2048)
    description: str = Field(min_length=10, max_length=5000)
    kind: Design.Kind = Design.Kind.LANDING
    tags: list[str] = Field(default_factory=list, max_length=20)
    industry: str = Field(default="", max_length=60)
    selector: str = Field(default="", max_length=200)
    viewport_width: int = Field(default=1440, ge=320, le=2560)

    @field_validator("title", "description", "industry", "selector", "source_url")
    @classmethod
    def safe_text(cls, value):
        if "\x00" in value or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError("Text contains invalid characters.")
        return value

    @field_validator("tags")
    @classmethod
    def tag_lengths(cls, tags):
        if any(not tag.strip() or len(tag) > 50 for tag in tags):
            raise ValueError("Tags must contain between 1 and 50 characters.")
        return tags
