import io
import logging
from datetime import timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image

from apps.catalogue.models import Design
from apps.catalogue.providers import EMBEDDING_MODEL, capture, embed

logger = logging.getLogger(__name__)


def process_design(pk):
    with transaction.atomic():
        design = Design.objects.select_for_update().get(pk=pk)
        if design.capture_status == Design.Status.READY:
            return
        if (
            design.capture_status == Design.Status.PROCESSING
            and design.processing_at
            and design.processing_at > timezone.now() - timedelta(minutes=10)
        ):
            return
        design.capture_status = Design.Status.PROCESSING
        design.processing_at = timezone.now()
        design.capture_error = ""
        design.save(
            update_fields=["capture_status", "processing_at", "capture_error", "updated_at"]
        )
    stored = []
    try:
        content = capture(design)
        with Image.open(io.BytesIO(content)) as source:
            source.load()
            # Crop the first viewport before resizing; full-page shrinking blurs cards.
            preview = source.crop((0, 0, source.width, min(source.height, source.width * 2 // 3)))
            preview.thumbnail((720, 480))
            output = io.BytesIO()
            preview.convert("RGB").save(output, format="JPEG", quality=80)
        design.screenshot.save(f"{design.pk}.jpg", ContentFile(content), save=False)
        stored.append(design.screenshot.name)
        design.thumbnail.save(f"{design.pk}.jpg", ContentFile(output.getvalue()), save=False)
        stored.append(design.thumbnail.name)
        design.capture_status = Design.Status.READY
        design.captured_at = timezone.now()
        design.save(
            update_fields=["screenshot", "thumbnail", "capture_status", "captured_at", "updated_at"]
        )
    except Exception as exc:
        for name in stored:
            design.screenshot.storage.delete(name)
        Design.objects.filter(pk=pk).update(
            capture_status=Design.Status.FAILED,
            capture_error=str(exc)[:180]
            if isinstance(exc, ValueError)
            else "Capture or storage failed. Check provider access and retry.",
        )
        logger.warning(
            "design.capture_failed", extra={"design_id": str(pk), "error.type": type(exc).__name__}
        )
        return
    try:
        text = " ".join(
            [
                design.title,
                design.kind,
                design.industry,
                design.description,
                " ".join(design.tags.values_list("name", flat=True)),
            ]
        )
        vector = embed(text)
        Design.objects.filter(pk=pk).update(
            embedding=vector, embedding_model=EMBEDDING_MODEL, embedding_error=""
        )
    except Exception:
        Design.objects.filter(pk=pk).update(
            embedding_error="Embedding unavailable; text search still works."
        )
