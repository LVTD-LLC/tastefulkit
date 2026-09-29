from uuid import UUID

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import File, Router, UploadedFile
from ninja.errors import HttpError

from apps.api.auth import api_key_auth, superuser_api_auth
from apps.catalogue.ingestion import IngestionUnavailable, submit_design
from apps.catalogue.models import Design
from apps.catalogue.schemas import DesignIn, SiteLinkIn
from apps.catalogue.services import design_detail, design_page, serialize_design
from apps.catalogue.sites import prepare_site, resolve_site

router = Router(tags=["designs"], auth=api_key_auth)


@router.post(
    "", auth=superuser_api_auth, response={200: dict, 201: dict, 401: dict, 422: dict, 503: dict}
)
def create_design(
    request,
    payload: DesignIn,
    screenshot: File[UploadedFile],
    thumbnail: File[UploadedFile],
    design_md: File[UploadedFile],
):
    """Admin-only prepared submission: store supplied assets and index supplied vector.

    Multipart fields: payload (JSON), screenshot, thumbnail, design_md (UTF-8 DESIGN.md).
    No captures, transformations, inference or background enrichment are performed.
    """
    try:
        design, created = submit_design(
            payload, request.auth.user, screenshot, thumbnail, design_md
        )
    except ValueError as exc:
        raise HttpError(422, str(exc)) from None
    except IngestionUnavailable:
        raise HttpError(
            503, "Storage or indexing unavailable. Retry the complete submission."
        ) from None
    return (201 if created else 200), serialize_design(
        design, admin=True, detail=True, include_design_markdown=True
    )


@router.get("", response={200: dict, 401: dict, 402: dict, 422: dict})
def list_designs(
    request,
    q: str = "",
    kind: str = "",
    tag: str = "",
    industry: str = "",
    page: int = 1,
    site: UUID | None = None,
):
    """Search published designs with text, semantic similarity, and filters."""
    return design_page(q, kind, tag, industry, page, site=site)


@router.get("/{design_id}", response={200: dict, 401: dict, 402: dict, 404: dict, 422: dict})
def get_design(request, response: HttpResponse, design_id: UUID):
    response["Cache-Control"] = "private, no-store"
    return design_detail(design_id, request.auth.user)


@router.patch(
    "/{design_id}/site",
    auth=superuser_api_auth,
    response={200: dict, 401: dict, 404: dict, 422: dict},
)
def link_design_site(request, design_id: UUID, payload: SiteLinkIn):
    """Attach or clear a site without replacing assets, guides, or embeddings."""
    try:
        data = prepare_site(payload.site.model_dump() if payload.site else None)
    except ValueError as exc:
        raise HttpError(422, str(exc)) from None
    with transaction.atomic():
        design = get_object_or_404(Design.objects.select_for_update(), pk=design_id)
        design.site = resolve_site(data)
        design.save(update_fields=["site", "updated_at"])
    return serialize_design(design, admin=True, detail=True, include_design_markdown=True)
