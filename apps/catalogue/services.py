import hashlib

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django_q.tasks import async_task

from apps.catalogue.models import Design, Tag
from apps.catalogue.providers import embed, public_url
from apps.catalogue.vector_store import search_vectors


def submit_design(payload, user):
    data = payload.model_dump()
    tags = sorted({slugify(tag) for tag in data.pop("tags") if slugify(tag)})
    data["source_url"] = public_url(data["source_url"])
    identity = "\n".join(str(data[k]) for k in ("source_url", "kind", "selector", "viewport_width"))
    fingerprint = hashlib.sha256(identity.encode()).hexdigest()
    with transaction.atomic():
        design, created = Design.objects.get_or_create(
            fingerprint=fingerprint, defaults={**data, "submitted_by": user}
        )
        if created:
            design.tags.set([Tag.objects.get_or_create(name=tag)[0] for tag in tags])
            transaction.on_commit(lambda: queue_capture(design.pk))
    return design, created


def queue_capture(pk):
    # A failed enqueue leaves a visible pending entry, recoverable by the admin retry action.
    try:
        async_task("apps.catalogue.tasks.process_design", str(pk), task_name=f"capture-{pk}")
    except Exception:
        Design.objects.filter(pk=pk).update(
            capture_status=Design.Status.FAILED,
            capture_error="Could not queue the capture. Check the worker and retry.",
        )


def visible_designs():
    return Design.objects.filter(published=True, capture_status=Design.Status.READY).defer(
        "embedding"
    )


def search_designs(query="", kind="", tag="", industry="", *, saved_by=None):
    query, kind, tag, industry = [clean_search_text(v) for v in (query, kind, tag, industry)]
    designs = visible_designs().prefetch_related("tags")
    if kind:
        designs = designs.filter(kind=kind)
    if tag:
        designs = designs.filter(tags__name=tag)
    if industry:
        designs = designs.filter(industry__iexact=industry)
    if saved_by is not None:
        designs = designs.filter(saves__user=saved_by)
    designs = designs.distinct()
    if not query.strip():
        return designs, "recent"
    query = query.strip()[:300]
    lexical = designs
    for word in query.split()[:12]:
        lexical = lexical.filter(
            Q(title__icontains=word)
            | Q(description__icontains=word)
            | Q(tags__name__icontains=word)
            | Q(industry__icontains=word)
        )
    lexical_ids = list(lexical.values_list("id", flat=True).distinct())
    try:
        query_vector = embed(query)
        ranked = search_vectors(designs, query_vector)
    except Exception:
        return lexical.distinct(), "text"
    ids = list(dict.fromkeys(lexical_ids + [pk for pk, _ in ranked]))
    by_id = {design.pk: design for design in designs.filter(pk__in=ids)}
    return [by_id[pk] for pk in ids if pk in by_id], "semantic"


def serialize_design(design, *, admin=False):
    result = {
        "id": str(design.pk),
        "title": design.title,
        "source_url": design.source_url,
        "description": design.description,
        "kind": design.kind,
        "industry": design.industry,
        "tags": [tag.name for tag in design.tags.all()],
        "selector": design.selector,
        "viewport_width": design.viewport_width,
        "capture_status": design.capture_status,
        "screenshot_url": design.screenshot.url if design.screenshot else None,
        "thumbnail_url": design.thumbnail.url if design.thumbnail else None,
        "created_at": design.created_at.isoformat(),
        "captured_at": design.captured_at.isoformat() if design.captured_at else None,
    }
    if admin:
        result.update(capture_error=design.capture_error, embedding_error=design.embedding_error)
    return result


def clean_search_text(value):
    return value.replace("\x00", "").encode("utf-8", "replace").decode()[:300]


def design_page(query="", kind="", tag="", industry="", page=1):
    """Shared REST/MCP search, visibility, pagination and screenshot serialization."""
    designs, mode = search_designs(query, kind, tag, industry)
    pager = Paginator(designs, 24)
    current = pager.get_page(page)
    return {
        "items": [serialize_design(design) for design in current],
        "page": current.number,
        "pages": pager.num_pages,
        "total": pager.count,
        "search_mode": mode,
    }


def design_detail(design_id, user):
    admin = user.is_active and user.is_superuser
    designs = Design.objects.all().defer("embedding") if admin else visible_designs()
    design = get_object_or_404(designs.prefetch_related("tags"), pk=design_id)
    return serialize_design(design, admin=admin)


def retry_design_capture(design_id):
    """Retry an eligible capture after the caller has enforced admin authorization."""
    design = get_object_or_404(Design, pk=design_id)
    if design.capture_status not in {Design.Status.FAILED, Design.Status.PENDING}:
        raise ValueError("Only pending or failed entries can be retried.")
    queue_capture(design.pk)
    return {"queued": True, "id": str(design.pk)}


def design_filters(page=1):
    """Discover filter values from visible designs only, in bounded pages."""
    visible = visible_designs()
    tags = Tag.objects.filter(designs__in=visible).order_by("name").distinct()
    industries = (
        visible.exclude(industry="")
        .order_by("industry")
        .values_list("industry", flat=True)
        .distinct()
    )
    tag_page = Paginator(tags.values_list("name", flat=True), 100).get_page(page)
    industry_page = Paginator(industries, 100).get_page(page)
    return {
        "kinds": [{"value": value, "label": label} for value, label in Design.Kind.choices],
        "tags": list(tag_page),
        "industries": list(industry_page),
        "tags_page": tag_page.number,
        "tags_pages": tag_page.paginator.num_pages,
        "industries_page": industry_page.number,
        "industries_pages": industry_page.paginator.num_pages,
    }
