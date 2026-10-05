"""Homepage content negotiation must work at /, not a separate docs URL."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from apps.catalogue.views import landing


@pytest.mark.parametrize(
    ("accept", "markdown"),
    [
        ("text/markdown", True),
        ("text/markdown; charset=utf-8", True),
        ("text/html;q=0.3, text/markdown;q=0.9", True),
        ("text/html", False),
        ("text/markdown;q=0.2, text/html;q=0.9", False),
        ("text/markdown;q=0, text/html", False),
        ("*/*", False),
        ("text/*", False),
        (None, False),
    ],
)
def test_homepage_negotiates_content(accept, markdown):
    request = RequestFactory().get("/", **({"HTTP_ACCEPT": accept} if accept else {}))
    request.user = AnonymousUser()
    with (
        patch("apps.catalogue.views.ranked_designs", return_value=([], "global")),
        patch("apps.catalogue.views.render", return_value=HttpResponse("<!doctype html>")),
    ):
        response = landing(request)
    assert response.status_code == 200
    assert "accept" in {value.strip().lower() for value in response["Vary"].split(",")}
    assert "no-store" in response["Cache-Control"]
    if markdown:
        assert response["Content-Type"] == "text/markdown; charset=utf-8"
        body = response.content.decode()
        assert body.startswith("# TastefulKit")
        assert "Find your taste" in body
        for path in [
            "/explore/",
            "/arena/",
            "/ui-libraries/",
            "/ai-skills/",
            "/how-to-use/",
            "/docs/",
            "/sitemap.xml",
        ]:
            assert f"]({path})" in body
        assert "<!doctype html>" not in body
    else:
        assert response["Content-Type"].startswith("text/html")
        assert response.content == b"<!doctype html>"


def test_markdown_ranking_titles_cannot_inject_links_or_html():
    request = RequestFactory().get("/", HTTP_ACCEPT="text/markdown")
    request.user = AnonymousUser()
    design = SimpleNamespace(
        title="[Injected](https://example.com)\n<script>alert(1)</script>",
        get_absolute_url=lambda: "/designs/00000000-0000-0000-0000-000000000001/",
    )
    with patch("apps.catalogue.views.ranked_designs", return_value=([design], "global")):
        body = landing(request).content.decode()
    import markdown

    html = markdown.markdown(body)
    assert '<a href="https://example.com"' not in html
    assert "<script>" not in html
    assert f'href="{design.get_absolute_url()}"' in html
