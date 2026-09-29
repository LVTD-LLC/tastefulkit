"""Public UI library directory and shared metadata serialization."""

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache

from apps.catalogue.models import Design
from apps.catalogue.navigation import discovery_navigation
from apps.catalogue.services import clean_search_text, visible_designs


def visible_libraries():
    return (
        visible_designs()
        .filter(kind=Design.Kind.UI_LIBRARY, ui_library__isnull=False)
        .select_related("ui_library", "site")
        .prefetch_related("tags")
    )


def library_metadata(design):
    item = getattr(design, "ui_library", None)
    if item is None:
        return None
    return {
        "website_url": item.website_url,
        "github_url": item.github_url,
        "frameworks": item.frameworks,
        "notes": item.notes,
        "pricing": item.pricing,
        "pricing_url": item.pricing_url,
        "pricing_checked_at": item.pricing_checked_at.isoformat()
        if item.pricing_checked_at
        else None,
    }


def library_results(query=""):
    items = visible_libraries()
    for word in clean_search_text(query).split()[:12]:
        items = items.filter(
            Q(title__icontains=word)
            | Q(description__icontains=word)
            | Q(ui_library__notes__icontains=word)
            | Q(ui_library__frameworks__icontains=word)
        )
    return items


@never_cache
def directory(request):
    query = clean_search_text(request.GET.get("q", ""))
    page = Paginator(library_results(query), 24).get_page(request.GET.get("page"))
    return render(
        request,
        "catalogue/ui_libraries.html",
        {
            "page": page,
            "q": query,
            **discovery_navigation(Design.Kind.UI_LIBRARY, "explore"),
            "canonical_url": settings.SITE_URL.rstrip("/") + "/ui-libraries/",
        },
    )


@never_cache
def detail(request, pk):
    design = get_object_or_404(visible_libraries(), pk=pk)
    return render(
        request,
        "catalogue/ui_library_detail.html",
        {
            "design": design,
            "library": design.ui_library,
            "canonical_url": settings.SITE_URL.rstrip("/") + design.get_absolute_url(),
        },
    )
