from uuid import UUID

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from ninja import File, Router, UploadedFile
from ninja.errors import HttpError

from apps.api.auth import api_key_auth, superuser_api_auth
from apps.catalogue.ingestion import IngestionUnavailable, submit_design
from apps.catalogue.libraries import library_results, visible_libraries
from apps.catalogue.schemas import UILibraryIn
from apps.catalogue.services import serialize_design

router = Router(tags=["ui-libraries"], auth=api_key_auth)


@router.post(
    "",
    auth=superuser_api_auth,
    include_in_schema=False,
    response={200: dict, 201: dict, 401: dict, 422: dict, 503: dict},
)
def create_library(
    request,
    payload: UILibraryIn,
    screenshot: File[UploadedFile],
    thumbnail: File[UploadedFile],
    design_md: File[UploadedFile],
):
    try:
        design, created = submit_design(
            payload, request.auth.user, screenshot, thumbnail, design_md, library=True
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


@router.get("", response={200: dict, 401: dict, 422: dict})
def list_libraries(request, q: str = "", page: int = 1):
    current = Paginator(library_results(q), 24).get_page(page)
    return {
        "items": [serialize_design(item) for item in current],
        "page": current.number,
        "pages": current.paginator.num_pages,
        "total": current.paginator.count,
    }


@router.get("/{library_id}", response={200: dict, 401: dict, 404: dict, 422: dict})
def get_library(request, library_id: UUID):
    return serialize_design(
        get_object_or_404(visible_libraries(), pk=library_id),
        detail=True,
        include_design_markdown=True,
    )
