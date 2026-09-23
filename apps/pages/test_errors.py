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
