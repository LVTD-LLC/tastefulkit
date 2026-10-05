from unittest.mock import patch

import pytest
from django.db import OperationalError


@pytest.mark.parametrize(
    ("path", "expected_status", "location"),
    [
        ("/blog", 301, "/blog/"),
        ("/docs/api-reference/mcp", 301, "/docs/api-reference/mcp/"),
        ("/blog?source=reference", 301, "/blog/?source=reference"),
        ("/missing-public-page/", 404, None),
        ("/blog/missing-article/", 404, None),
        ("/docs/missing/page/", 404, None),
    ],
)
@pytest.mark.parametrize("method", ["get", "head"])
def test_public_error_routes_do_not_depend_on_database(
    client, settings, path, expected_status, location, method
):
    settings.DEBUG = False
    settings.POSTHOG_API_KEY = "public-test-capture-key"
    # A 404 is also rendered before CommonMiddleware appends a missing slash.
    # Error handling must still work when optional context queries cannot run.
    with patch(
        "django.db.backends.base.base.BaseDatabaseWrapper.cursor",
        side_effect=OperationalError("the connection is closed"),
    ) as cursor:
        response = getattr(client, method)(path)

    assert response.status_code == expected_status
    cursor.assert_not_called()
    if location:
        assert response["Location"] == location
    elif method == "get":
        content = response.content.decode()
        assert "Page not found" in content
        assert '<meta name="robots" content="noindex, follow"' in content
        assert content.count("<h1") == 1
        assert 'href="/"' in content
        assert "application/ld+json" not in content
        assert "posthog" not in content.lower()
        assert "public-test-capture-key" not in content
        assert path not in content


@pytest.mark.parametrize("path", ["/some-path-that-does-not-exist", "/docs/missing/page/"])
def test_missing_page_returns_markdown_when_requested(client, settings, path):
    settings.DEBUG = False
    response = client.get(path, HTTP_ACCEPT="text/markdown", follow=True)

    assert response.status_code == 404
    assert response["Content-Type"] == "text/markdown; charset=utf-8"
    body = response.content.decode()
    assert body.startswith("# 404")
    assert len(body) >= 20
    assert "[Documentation](/docs/)" in body
    assert "[Sitemap](/sitemap.xml)" in body
    assert "Accept" in response["Vary"]


@pytest.mark.parametrize(
    ("accept", "content_type"),
    [
        ("text/html", "text/html"),
        ("*/*", "text/html"),
        ("text/*", "text/html"),
        ("text/markdown;q=0, text/html", "text/html"),
        ("text/markdown;q=0.5, text/html;q=1", "text/html"),
        ("text/html;q=0.5, text/markdown;q=1", "text/markdown"),
    ],
)
def test_missing_page_respects_accept_preferences(client, settings, accept, content_type):
    settings.DEBUG = False
    response = client.get("/some-path-that-does-not-exist", HTTP_ACCEPT=accept)

    assert response.status_code == 404
    assert response["Content-Type"].startswith(content_type)
    assert "Accept" in response["Vary"]


def test_missing_page_defaults_to_html(client, settings):
    settings.DEBUG = False
    response = client.get("/some-path-that-does-not-exist")

    assert response.status_code == 404
    assert response["Content-Type"].startswith("text/html")
    assert b"<html" in response.content


def test_markdown_head_preserves_status_and_headers_without_body(client, settings):
    settings.DEBUG = False
    response = client.head("/some-path-that-does-not-exist", HTTP_ACCEPT="text/markdown")

    assert response.status_code == 404
    assert response["Content-Type"] == "text/markdown; charset=utf-8"
    assert "Accept" in response["Vary"]
    assert response.content == b""
