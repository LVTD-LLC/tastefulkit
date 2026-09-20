"""Public, revocable social previews of published landing-page references."""

import logging
from hashlib import sha256
from io import BytesIO

from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from PIL import Image

from apps.catalogue.models import Design
from apps.catalogue.services import visible_designs
from apps.pages.social_images import render_social_image

logger = logging.getLogger(__name__)
MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024
MAX_THUMBNAIL_PIXELS = 4_000_000


def read_thumbnail(field):
    if not field:
        return None
    try:
        # Read only a stored file. Never fetch source URLs or request-supplied URLs.
        with field.open("rb") as source:
            content = source.read(MAX_THUMBNAIL_BYTES + 1)
        if len(content) > MAX_THUMBNAIL_BYTES:
            raise ValueError("Thumbnail is too large")
        with Image.open(BytesIO(content)) as image:
            if image.width * image.height > MAX_THUMBNAIL_PIXELS:
                raise ValueError("Thumbnail dimensions are too large")
            return image.convert("RGB")
    except Exception:
        # Storage is an external boundary; serve a branded text card if unavailable.
        logger.warning(
            "design.social_thumbnail.failed",
            extra={"event.name": "design.social_thumbnail.failed", "outcome": "failure"},
        )
        return None


@require_safe
@never_cache
def design_social_image(request, pk):
    # Recheck visibility BEFORE consulting the image cache, on every request.
    design = get_object_or_404(
        visible_designs()
        .filter(kind=Design.Kind.LANDING)
        .only("id", "title", "thumbnail", "updated_at"),
        pk=pk,
    )
    signature = (str(design.pk), design.title, design.thumbnail.name, design.updated_at.isoformat())
    key = "design-social:1:" + sha256(repr(signature).encode()).hexdigest()
    content = cache.get(key)
    if content is None:
        thumbnail = read_thumbnail(design.thumbnail)
        try:
            content = render_social_image(
                design.title,
                "A real reference for your next landing page.",
                "Landing page inspiration",
                thumbnail,
            )
        finally:
            if thumbnail is not None:
                thumbnail.close()
        cache.set(key, content, 3600 if thumbnail is not None else 60)
    response = HttpResponse(content, content_type="image/png")
    response["X-Content-Type-Options"] = "nosniff"
    return response
