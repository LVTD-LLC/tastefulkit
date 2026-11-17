"""Public discovery and metadata contracts for the browser-local brief builder."""

import json
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import resolve, reverse

from apps.pages import tools
from apps.pages.test_metadata import HeadMetadata
from tastefulkit.sitemaps import StaticViewSitemap


def render_tool(view, path):
    request = RequestFactory().get(path)
    request.user = AnonymousUser()
    request.session = {}
    request.resolver_match = resolve(path)
    # Optional site-shell context needs a DB, not this static view.
    with (
        patch("apps.core.context_processors.available_social_providers", return_value={}),
        patch("apps.pages.newsletter.context", return_value={}),
        patch("apps.pages.context_processors.referrer_banner", return_value={}),
    ):
        return view(request)


def test_tool_is_public_indexable_and_discoverable(settings):
    settings.SITE_URL = "https://tastefulkit.com"
    response = render_tool(tools.reference_brief, reverse("reference_brief"))
    assert response.status_code == 200
    html = response.content.decode()
    head = HeadMetadata()
    head.feed(html)
    assert head.tags["canonical"] == ["https://tastefulkit.com/tools/reference-brief/"]
    assert head.tags["robots"] == ["index, follow"]
    assert html.count("<h1>") == 1
    assert "data-reference-brief" in html
    assert "data-brief-copy" in html and "data-brief-download" in html
    assert "data-markdown-exclude" in html and "ph-no-capture" in html
    schema = json.loads(html.split('<script type="application/ld+json">')[1].split("</script>")[0])
    assert {item["@type"] for item in schema["@graph"]} == {"WebApplication", "BreadcrumbList"}
    assert schema["@graph"][0]["offers"]["price"] == "0"
    assert {"tools_index", "reference_brief"}.issubset(StaticViewSitemap().items())
    hub = render_tool(tools.tools_index, reverse("tools_index"))
    assert reverse("reference_brief") in hub.content.decode()


def test_tool_rejects_submission_without_processing_user_text():
    request = RequestFactory().post(reverse("reference_brief"), {"private_note": "do-not-process"})
    response = tools.reference_brief(request)
    assert response.status_code == 405
    assert b"do-not-process" not in response.content
