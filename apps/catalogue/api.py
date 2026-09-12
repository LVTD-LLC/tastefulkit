from uuid import UUID

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field, field_validator

from apps.api.auth import api_key_auth, superuser_api_auth
from apps.catalogue.models import Design
from apps.catalogue.services import (
    queue_capture,
    search_designs,
    serialize_design,
    submit_design,
    visible_designs,
)

router = Router(tags=["designs"], auth=api_key_auth)


class DesignIn(Schema):
    title: str = Field(min_length=2, max_length=160)
    source_url: str = Field(max_length=2048)
    description: str = Field(min_length=10, max_length=5000)
    kind: Design.Kind = Design.Kind.LANDING
    tags: list[str] = Field(default_factory=list, max_length=20)
    industry: str = Field(default="", max_length=60)
    selector: str = Field(default="", max_length=200)
    viewport_width: int = Field(default=1440, ge=320, le=2560)

    @field_validator("tags")
    @classmethod
    def tag_lengths(cls, tags):
        if any(not tag.strip() or len(tag) > 50 for tag in tags):
            raise ValueError("Tags must contain between 1 and 50 characters.")
        return tags


@router.post("", auth=superuser_api_auth, response={200: dict, 201: dict, 401: dict, 422: dict})
def create_design(request, payload: DesignIn):
    """Admin-only, idempotent submission. Captures and embeds asynchronously."""
    try:
        design, created = submit_design(payload, request.auth.user)
    except ValueError as exc:
        raise HttpError(422, str(exc)) from None
    design.refresh_from_db()
    return (201 if created else 200), serialize_design(design, admin=True)


@router.get("", response={200: dict, 401: dict, 422: dict})
def list_designs(
    request, q: str = "", kind: str = "", tag: str = "", industry: str = "", page: int = 1
):
    """Search published designs with text, semantic similarity, and filters."""
    designs, mode = search_designs(q, kind, tag, industry)
    pager = Paginator(designs, 24)
    current = pager.get_page(page)
    return {
        "items": [serialize_design(d) for d in current],
        "page": current.number,
        "pages": pager.num_pages,
        "total": pager.count,
        "search_mode": mode,
    }


@router.get("/{design_id}", response={200: dict, 401: dict, 404: dict, 422: dict})
def get_design(request, design_id: UUID):
    admin = request.auth.user.is_superuser
    design = get_object_or_404(Design.objects.all() if admin else visible_designs(), pk=design_id)
    return serialize_design(design, admin=admin)


@router.post(
    "/{design_id}/retry",
    auth=superuser_api_auth,
    response={200: dict, 401: dict, 404: dict, 409: dict, 422: dict},
)
def retry_design(request, design_id: UUID):
    design = get_object_or_404(Design, pk=design_id)
    if design.capture_status not in {Design.Status.FAILED, Design.Status.PENDING}:
        raise HttpError(409, "Only pending or failed entries can be retried.")
    queue_capture(design.pk)
    return {"queued": True, "id": str(design.pk)}
