from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.billing.access import has_paid_access, paid_required
from apps.catalogue.arena import ranked_designs
from apps.catalogue.models import Design, SavedDesign, Tag
from apps.catalogue.services import search_designs, visible_designs


@never_cache
def landing(request):
    designs, _ = ranked_designs(request.user, mode="global", kind=Design.Kind.LANDING)
    return render(request, "pages/landing-page.html", {"designs": designs[:6]})


@paid_required
def library(request):
    query = request.GET.get("q", "")[:300]
    kind = Design.Kind.LANDING
    tag = request.GET.get("tag", "")
    industry = request.GET.get("industry", "")
    saved = request.GET.get("saved") == "1"
    designs, mode = search_designs(
        query, kind, tag, industry, saved_by=request.user if saved else None
    )
    page = Paginator(designs, 24).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "catalogue/library.html",
        {
            "page": page,
            "q": query,
            "kind": kind,
            "tag": tag,
            "industry": industry,
            "saved": saved,
            "search_mode": mode,
            "kinds": Design.Kind.choices,
            "tags": Tag.objects.filter(designs__in=visible_designs()).distinct(),
            "industries": visible_designs()
            .exclude(industry="")
            .values_list("industry", flat=True)
            .order_by("industry")
            .distinct(),
            "query_params": params.urlencode(),
        },
    )


@never_cache
def detail(request, pk):
    if not has_paid_access(request.user):
        design = get_object_or_404(
            visible_designs().filter(kind=Design.Kind.LANDING).only("id", "title", "thumbnail"),
            pk=pk,
        )
        return render(
            request,
            "catalogue/teaser.html",
            {
                "design_id": design.pk,
                "design_title": design.title,
                "preview_thumbnail_url": design.thumbnail.url if design.thumbnail else "",
            },
        )
    design = get_object_or_404(visible_designs().prefetch_related("tags"), pk=pk)
    return render(
        request,
        "catalogue/detail.html",
        {
            "design": design,
            "is_saved": SavedDesign.objects.filter(user=request.user, design=design).exists(),
        },
    )


@paid_required
@require_POST
def save_design(request, pk):
    design = get_object_or_404(visible_designs(), pk=pk)
    if request.POST.get("action") == "remove":
        SavedDesign.objects.filter(user=request.user, design=design).delete()
    else:
        SavedDesign.objects.get_or_create(user=request.user, design=design)
    return redirect(design)


@paid_required
def design_markdown(request, pk):
    design = get_object_or_404(visible_designs().exclude(design_markdown=""), pk=pk)
    response = HttpResponse(design.design_markdown, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="DESIGN.md"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
