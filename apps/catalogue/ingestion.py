"""The sole creation path: accept a complete, agent-prepared reference."""

import hashlib
import logging
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify

from apps.catalogue.artifacts import read_design_markdown, read_image
from apps.catalogue.models import Design, Tag
from apps.catalogue.providers import public_url
from apps.catalogue.vector_store import (
    remove_vector,
    restore_vector,
    snapshot_vector,
    upsert_vector,
)

logger = logging.getLogger(__name__)


class IngestionUnavailable(Exception):
    pass


def _log_failure(event, design_id, exc):
    logger.warning(
        event,
        extra={
            "event.name": event,
            "design_id": str(design_id),
            "error.type": type(exc).__name__,
            "outcome": "failure",
        },
    )


def _cleanup_files(storage, names, design_id):
    for name in names:
        try:
            storage.delete(name)
        except Exception as exc:
            _log_failure("design.asset_cleanup.failed", design_id, exc)


def submit_design(payload, user, screenshot, thumbnail, design_md):
    if not user.is_active or not user.is_superuser:
        raise PermissionError("Only active administrators can submit designs.")
    data = payload.model_dump()
    replace = data.pop("replace_existing")
    vector = data.pop("embedding")
    tags = sorted({slugify(tag) for tag in data.pop("tags") if slugify(tag)})
    data["source_url"] = public_url(data["source_url"])
    identity = "\n".join(str(data[k]) for k in ("source_url", "kind", "selector", "viewport_width"))
    fingerprint = hashlib.sha256(identity.encode()).hexdigest()
    data["design_markdown"] = read_design_markdown(design_md)
    shot = read_image(
        screenshot, viewport_width=None if data["selector"] else data["viewport_width"]
    )
    thumb = read_image(thumbnail, thumbnail=True)
    stored = []
    design_id = None
    previous = None
    index_updated = False
    storage = Design._meta.get_field("screenshot").storage
    try:
        with transaction.atomic():
            design, created = Design.objects.get_or_create(
                fingerprint=fingerprint, defaults={**data, "submitted_by": user, "published": False}
            )
            # Serializes duplicate/replacement requests for the same reference.
            design = Design.objects.select_for_update().get(pk=design.pk)
            design_id = design.pk
            if not created and not replace:
                return design, False
            old_files = [field.name for field in (design.screenshot, design.thumbnail) if field]
            previous = snapshot_vector(design.pk) if not created else None
            for key, value in data.items():
                setattr(design, key, value)
            for field, (content, extension) in (
                (design.screenshot, shot),
                (design.thumbnail, thumb),
            ):
                field.save(
                    f"{design.pk}-{uuid4().hex}.{extension}", ContentFile(content), save=False
                )
                stored.append(field.name)
            design.capture_status = Design.Status.READY
            design.capture_error = design.embedding_error = ""
            design.processing_at = None
            if created:
                design.published = True
            design.save()
            design.tags.set([Tag.objects.get_or_create(name=tag)[0] for tag in tags])
            try:
                # Indexing supplied data is synchronous persistence, not enrichment.
                upsert_vector(design.pk, vector)
                index_updated = True
            except Exception:
                _restore_index(design.pk, previous)
                raise
            transaction.on_commit(lambda: _cleanup_files(storage, old_files, design.pk))
        return design, created
    except Exception as exc:
        if index_updated:
            _restore_index(design_id, previous)
        _cleanup_files(storage, stored, design_id)
        _log_failure("design.ingestion.failed", design_id, exc)
        raise IngestionUnavailable from exc


def _restore_index(pk, previous):
    try:
        if previous is None:
            remove_vector(pk)
        else:
            restore_vector(previous)
    except Exception as exc:
        _log_failure("design.index_restore.failed", pk, exc)
