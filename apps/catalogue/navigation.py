"""Shared discovery navigation; type selection survives changes of surface."""

from urllib.parse import urlencode

from django.urls import reverse

from apps.catalogue.models import Design
from apps.catalogue.services import visible_kinds


def selected_kind(request):
    params = request.POST if request.method == "POST" else request.GET
    value = params.get("kind")
    return value if value in Design.Kind.values else Design.Kind.LANDING


def discovery_navigation(kind, section):
    def destination(surface, value):
        params = {"kind": value}
        if surface == "explore":
            route = "ui_libraries" if value == Design.Kind.UI_LIBRARY else "library"
            if route == "ui_libraries":
                params = {}
        else:
            route = "voting_arena" if surface == "arena" else "design_rankings"
            if surface == "personal":
                params = {"mode": "personal", **params}
        return reverse(route) + ("?" + urlencode(params) if params else "")

    types = dict(visible_kinds())
    types.update({Design.Kind.UI_LIBRARY: "UI libraries", Design.Kind.LANDING: "Landing pages"})
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
            for value in Design.Kind.values
            if value in types
        ],
    }
