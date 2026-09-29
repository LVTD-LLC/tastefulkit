from datetime import date
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from ninja import Schema
from pydantic import (
    AliasChoices,
    AwareDatetime,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from apps.catalogue.models import Design
from apps.catalogue.providers import EMBEDDING_MODEL
from apps.catalogue.vector_store import validate_vector


class SiteIn(Schema):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("name", "url")
    @classmethod
    def valid_text(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError("Use nonempty text without control characters.")
        return value


class SiteLinkIn(Schema):
    model_config = ConfigDict(extra="forbid")
    site: SiteIn | None


class DesignIn(Schema):
    model_config = ConfigDict(extra="forbid")

    captured_at: AwareDatetime
    embedding_model: Literal[EMBEDDING_MODEL]
    embedding: list[float] = Field(min_length=768, max_length=768)
    replace_existing: bool = False
    site: SiteIn | None = None

    @field_validator("embedding")
    @classmethod
    def valid_embedding(cls, value):
        validate_vector(value)
        return value

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


class LibraryPriceIn(Schema):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="", max_length=100)
    billing: Literal["free", "one_time", "recurring", "contact"]
    amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="", pattern=r"^(?:[A-Z]{3})?$")
    interval: Literal["", "month", "year"] = ""
    notes: str = Field(default="", max_length=1000)

    @field_validator("name", "notes")
    @classmethod
    def valid_text(cls, value):
        return DesignIn.safe_text(value)

    @model_validator(mode="after")
    def consistent_price(self):
        if self.billing in {"one_time", "recurring"} and (self.amount is None or not self.currency):
            raise ValueError("Paid plans require an amount and currency.")
        if (self.billing == "recurring") != bool(self.interval):
            raise ValueError("Only recurring plans require a month/year interval.")
        if self.billing == "free" and self.amount not in (None, Decimal(0)):
            raise ValueError("Free plans cannot have a nonzero price.")
        if self.billing == "contact" and self.amount is not None:
            raise ValueError("Contact pricing has no known amount.")
        return self


class LibraryMetadataIn(Schema):
    model_config = ConfigDict(extra="forbid")
    website_url: str = Field(default="", max_length=2048)
    github_url: str = Field(default="", max_length=2048)
    frameworks: list[str] = Field(default_factory=list, max_length=20)
    notes: str = Field(default="", max_length=10000)
    pricing: list[LibraryPriceIn] = Field(default_factory=list, max_length=20)
    pricing_url: str = Field(default="", max_length=2048)
    pricing_checked_at: date | None = None

    @field_validator("website_url", "github_url", "pricing_url")
    @classmethod
    def valid_link(cls, value, info):
        if not value:
            return value
        try:
            URLValidator(schemes=["https", "http"])(value)
            parts = urlsplit(value)
            if parts.username or parts.password or parts.port not in (None, 80, 443):
                raise ValueError()
            if info.field_name == "github_url" and (
                parts.hostname != "github.com"
                or len(parts.path.strip("/").split("/")) != 2
                or parts.query
                or parts.fragment
            ):
                raise ValueError()
        except (ValueError, ValidationError):
            raise ValueError(
                "Use a public HTTP(S) URL; GitHub links must identify a repository."
            ) from None
        return value

    @field_validator("frameworks")
    @classmethod
    def valid_frameworks(cls, values):
        values = list(dict.fromkeys(value.strip() for value in values))
        if any(
            not value
            or len(value) > 60
            or "\x00" in value
            or any(0xD800 <= ord(c) <= 0xDFFF for c in value)
            for value in values
        ):
            raise ValueError("Framework labels must be 1–60 characters.")
        return values

    @field_validator("notes")
    @classmethod
    def valid_content(cls, value):
        text = value
        if "\x00" in text or any(0xD800 <= ord(c) <= 0xDFFF for c in text):
            raise ValueError("Text contains invalid characters.")
        return value


class UILibraryIn(DesignIn):
    title: str = Field(min_length=2, max_length=160, validation_alias=AliasChoices("name", "title"))
    kind: Literal["ui_library"] = "ui_library"
    selector: Literal[""] = ""
    library: LibraryMetadataIn
