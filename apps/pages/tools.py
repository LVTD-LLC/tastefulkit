"""Public, browser-local tools. User-entered briefs never reach a view."""

import json

from django.conf import settings
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_safe


@require_safe
def tools_index(request):
    return render(request, "pages/tools/index.html")


@require_safe
def reference_brief(request):
    origin = settings.SITE_URL.rstrip("/")
    url = origin + reverse("reference_brief")
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebApplication",
                "name": "TastefulKit Design Reference Brief Builder",
                "url": url,
                "applicationCategory": "DesignApplication",
                "operatingSystem": "Web browser",
                "browserRequirements": "Requires JavaScript",
                "description": (
                    "Turn your reference observations into an editable Markdown decision brief."
                ),
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
                "creator": {"@type": "Organization", "name": "TastefulKit", "url": origin},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Tools",
                        "item": origin + reverse("tools_index"),
                    },
                    {"@type": "ListItem", "position": 2, "name": "Reference brief", "item": url},
                ],
            },
        ],
    }
    return render(
        request,
        "pages/tools/reference_brief.html",
        {"schema_json": json.dumps(schema).replace("<", "\\u003c")},
    )
