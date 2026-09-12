from uuid import UUID

from ninja import Router
from ninja.errors import HttpError

from apps.api.auth import api_key_auth, superuser_api_auth
from apps.catalogue.schemas import DesignIn
from apps.catalogue.services import (
    design_detail,
    design_page,
    retry_design_capture,
    serialize_design,
    submit_design,
)

router = Router(tags=["designs"], auth=api_key_auth)


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
    return design_page(q, kind, tag, industry, page)


@router.get("/{design_id}", response={200: dict, 401: dict, 404: dict, 422: dict})
def get_design(request, design_id: UUID):
    return design_detail(design_id, request.auth.user)


@router.post(
    "/{design_id}/retry",
    auth=superuser_api_auth,
    response={200: dict, 401: dict, 404: dict, 409: dict, 422: dict},
)
def retry_design(request, design_id: UUID):
    try:
        return retry_design_capture(design_id)
    except ValueError as exc:
        raise HttpError(409, str(exc)) from None
