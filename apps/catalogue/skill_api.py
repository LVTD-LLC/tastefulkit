"""Separate JSON ingestion: skills need no screenshot, DESIGN.md or embedding."""

from datetime import date
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import URLValidator
from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from pydantic import ConfigDict, Field, field_validator

from apps.api.auth import api_key_auth, superuser_api_auth
from apps.catalogue.models import AISkill
from apps.catalogue.skills import serialize_skill, skill_results


class AISkillIn(Schema):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=160)
    source_url: str = Field(min_length=1, max_length=2048)
    website_url: str = Field(default="", max_length=2048)
    repository_url: str = Field(default="", max_length=2048)
    description: str = Field(min_length=10, max_length=5000)
    notes: str = Field(default="", max_length=10000)
    installation: str = Field(default="", max_length=10000)
    compatible_agents: list[str] = Field(default_factory=list, max_length=20)
    tags: list[str] = Field(default_factory=list, max_length=20)
    license: str = Field(default="", max_length=160)
    checked_at: date | None = None
    replace_existing: bool = False

    @field_validator("name", "description", "notes", "installation", "license")
    @classmethod
    def safe_text(cls, value):
        if any((ord(c) < 32 and c not in "\n\r\t") or 0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError("Text contains invalid characters.")
        return value

    @field_validator("source_url", "website_url", "repository_url")
    @classmethod
    def valid_link(cls, value):
        if not value:
            return value
        try:
            URLValidator(schemes=["https", "http"])(value)
            parts = urlsplit(value)
            if parts.username or parts.password or parts.port not in (None, 80, 443):
                raise ValueError()
            if any(ord(c) < 33 for c in value):
                raise ValueError()
        except (ValueError, ValidationError):
            raise ValueError("Use an HTTP(S) URL without credentials.") from None
        # Preserve paths and queries: a repository can contain many distinct skills.
        return urlunsplit(
            (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, "")
        )

    @field_validator("compatible_agents", "tags")
    @classmethod
    def valid_labels(cls, values):
        labels = list(dict.fromkeys(value.strip() for value in values))
        if any(
            not value
            or len(value) > 60
            or any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value)
            for value in labels
        ):
            raise ValueError("Labels must be 1–60 characters without control characters.")
        return labels


class AISkillOut(Schema):
    id: UUID
    url: str
    name: str
    source_url: str
    website_url: str
    repository_url: str
    description: str
    notes: str
    installation: str
    compatible_agents: list[str]
    tags: list[str]
    license: str
    checked_at: date | None


class AISkillListOut(Schema):
    items: list[AISkillOut]
    page: int
    pages: int
    total: int


router = Router(tags=["ai-skills"], auth=api_key_auth)


@router.post(
    "",
    auth=superuser_api_auth,
    include_in_schema=False,
    response={200: AISkillOut, 201: AISkillOut, 401: dict, 422: dict},
)
@transaction.atomic
def create_skill(request, payload: AISkillIn):
    data = payload.model_dump(exclude={"replace_existing"})
    source = data.pop("source_url")
    skill, created = AISkill.objects.get_or_create(
        source_url=source, defaults={**data, "submitted_by": request.auth.user}
    )
    if not created and payload.replace_existing:
        skill = AISkill.objects.select_for_update().get(pk=skill.pk)
        for field, value in data.items():
            setattr(skill, field, value)
        skill.save(update_fields=[*data, "updated_at"])
    return (201 if created else 200), serialize_skill(skill)


@router.get("", response={200: AISkillListOut, 401: dict, 422: dict})
def list_skills(request, q: str = "", page: int = 1):
    current = Paginator(skill_results(q), 24).get_page(page)
    return {
        "items": [serialize_skill(item) for item in current],
        "page": current.number,
        "pages": current.paginator.num_pages,
        "total": current.paginator.count,
    }


@router.get("/{skill_id}", response={200: AISkillOut, 401: dict, 404: dict, 422: dict})
def get_skill(request, skill_id: UUID):
    return serialize_skill(get_object_or_404(skill_results(), pk=skill_id))
