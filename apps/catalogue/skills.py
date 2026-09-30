"""Read-only public design-skill directory. Submitted instructions are inert text."""

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache

from apps.catalogue.models import AISkill
from apps.catalogue.navigation import discovery_navigation
from apps.catalogue.services import clean_search_text


def skill_results(query=""):
    items = AISkill.objects.filter(published=True)
    for word in clean_search_text(query).split()[:12]:
        items = items.filter(
            Q(name__icontains=word)
            | Q(description__icontains=word)
            | Q(notes__icontains=word)
            | Q(compatible_agents__icontains=word)
            | Q(tags__icontains=word)
        )
    return items


def serialize_skill(skill):
    fields = (
        "name",
        "source_url",
        "website_url",
        "repository_url",
        "description",
        "notes",
        "installation",
        "compatible_agents",
        "tags",
        "license",
    )
    return {
        "id": str(skill.pk),
        "url": skill.get_absolute_url(),
        **{field: getattr(skill, field) for field in fields},
        "checked_at": skill.checked_at.isoformat() if skill.checked_at else None,
    }


@never_cache
def directory(request):
    query = clean_search_text(request.GET.get("q", ""))
    return render(
        request,
        "catalogue/ai_skills.html",
        {
            "page": Paginator(skill_results(query), 24).get_page(request.GET.get("page")),
            "q": query,
            **discovery_navigation("ai_skill", "explore"),
            "canonical_url": settings.SITE_URL.rstrip("/") + "/ai-skills/",
        },
    )


@never_cache
def detail(request, pk):
    skill = get_object_or_404(skill_results(), pk=pk)
    return render(
        request,
        "catalogue/ai_skill_detail.html",
        {
            "skill": skill,
            "canonical_url": settings.SITE_URL.rstrip("/") + skill.get_absolute_url(),
        },
    )
