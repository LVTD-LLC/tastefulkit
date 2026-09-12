import io
import logging
from datetime import timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django_q.models import Schedule
from PIL import Image

from apps.catalogue.models import Design
from apps.catalogue.providers import EMBEDDING_MODEL, RetryableProviderError, capture, embed
from apps.catalogue.vector_store import upsert_vector

logger = logging.getLogger(__name__)


def process_design(pk, attempt=0):
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
    except RetryableProviderError as exc:
        if attempt < 3:
            schedule_capture_retry(design.pk, attempt + 1, exc.retry_after)
        else:
            Design.objects.filter(pk=pk).update(
                capture_status=Design.Status.FAILED,
                capture_error="Provider retries exhausted. Check quota and retry later.",
            )
        return
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
    index_design(pk)


def index_design(pk, attempt=0):
    design = Design.objects.filter(pk=pk, capture_status=Design.Status.READY).first()
    if design is None:
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
        upsert_vector(pk, vector)
        Design.objects.filter(pk=pk).update(embedding_model=EMBEDDING_MODEL, embedding_error="")
    except Exception as exc:
        Design.objects.filter(pk=pk).update(
            embedding_error="Vector indexing unavailable; text search still works."
        )
        logger.warning(
            "design.index_failed", extra={"design_id": str(pk), "error.type": type(exc).__name__}
        )
        if attempt < 3:
            # A distinct name avoids overwriting the currently executing one-shot schedule.
            Schedule.objects.update_or_create(
                name=f"index-retry-{pk}-{attempt + 1}",
                defaults={
                    "func": "apps.catalogue.tasks.index_design",
                    "args": repr(str(pk)),
                    "kwargs": f"attempt={attempt + 1}",
                    "schedule_type": Schedule.ONCE,
                    "repeats": -1,
                    "next_run": timezone.now() + timedelta(minutes=2**attempt),
                },
            )


def schedule_capture_retry(pk, attempt, delay):
    with transaction.atomic():
        Schedule.objects.update_or_create(
            name=f"capture-retry-{pk}",
            defaults={
                "func": "apps.catalogue.tasks.process_design",
                "args": repr(str(pk)),
                "kwargs": f"attempt={attempt}",
                "schedule_type": Schedule.ONCE,
                "repeats": -1,
                "next_run": timezone.now() + timedelta(seconds=delay * attempt),
            },
        )
        Design.objects.filter(pk=pk).update(
            capture_status=Design.Status.PENDING,
            capture_error=f"Provider busy; automatic retry {attempt}/3 scheduled.",
        )
