"""Shared discovery navigation; type selection survives changes of surface."""

from urllib.parse import urlencode

from django.urls import reverse

from apps.catalogue.models import Design
from apps.catalogue.services import visible_kinds

DIRECTORY_ROUTES = {Design.Kind.UI_LIBRARY: "ui_libraries", "ai_skill": "ai_skills"}


def selected_kind(request):
    params = request.POST if request.method == "POST" else request.GET
    value = params.get("kind")
    return value if value in [*Design.Kind.values, "ai_skill"] else Design.Kind.LANDING


def discovery_navigation(kind, section):
    def destination(surface, value):
        params = {"kind": value}
        if surface == "explore":
            route = DIRECTORY_ROUTES.get(value, "library")
            if value in DIRECTORY_ROUTES:
                params = {}
        else:
            if value in DIRECTORY_ROUTES:
                value = Design.Kind.LANDING
                params = {"kind": value}
            route = "voting_arena" if surface == "arena" else "design_rankings"
            if surface == "personal":
                params = {"mode": "personal", **params}
        return reverse(route) + ("?" + urlencode(params) if params else "")

    types = dict(visible_kinds())
    types.update({Design.Kind.UI_LIBRARY: "UI libraries", Design.Kind.LANDING: "Landing pages"})
    types["ai_skill"] = "AI skills"
    if kind != "ai_skill":
        types.setdefault(kind, Design.Kind(kind).label)
    return {
        "discovery_sections": [
            {"label": label, "url": destination(value, kind), "active": section == value}
            for value, label in [
                ("explore", "Explore"),
                ("arena", "Arena"),
                ("global", "Global ranking"),
                ("personal", "For you"),
            ]
        ],
        "discovery_types": [
            {"label": types[value], "url": destination(section, value), "active": kind == value}
            for value in [*Design.Kind.values, "ai_skill"]
            if value in types and (section == "explore" or value not in DIRECTORY_ROUTES)
        ],
    }
