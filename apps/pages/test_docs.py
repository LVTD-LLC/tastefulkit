from html.parser import HTMLParser
from urllib.parse import urlsplit

import pytest
from django.urls import reverse

from apps.pages.views import get_docs_navigation, get_flat_page_list

DOCS_PAGES = get_flat_page_list(get_docs_navigation())


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(value for key, value in attrs if key == "href")


@pytest.mark.django_db
def test_docs_home_is_public(client):
    response = client.get(reverse("docs_home"), follow=True)
    assert response.status_code == 200
    assert response.redirect_chain == [("/docs/getting-started/introduction/", 302)]


@pytest.mark.django_db
@pytest.mark.parametrize("page", DOCS_PAGES, ids=lambda page: page["url"])
@pytest.mark.parametrize("reader", ["anonymous", "unpaid", "paid"])
def test_docs_pages_and_links_are_public(
    client, django_user_model, settings, page, reader, grant_membership
):
    settings.SITE_URL = "https://tastefulkit.com"
    if reader != "anonymous":
        user = django_user_model.objects.create_user(
            username="docs-reader", email="private-reader@example.com"
        )
        if reader == "paid":
            grant_membership(user)
        client.force_login(user)

    response = client.get(page["url"])
    assert response.status_code == 200
    content = response.content.decode()
    assert 'content="index, follow"' in content
    assert f'href="https://tastefulkit.com{page["url"]}"' in content
    assert "data-docs-page" in content
    assert "private-reader@example.com" not in content
    assert "Deployment" not in content
    assert "Example Feature" not in content
    assert "{{" not in response.context["content"]
    if reader == "anonymous":
        assert 'href="/accounts/login/"' in content
        assert 'href="/accounts/signup/"' in content
        assert 'href="/accounts/logout/"' not in content
        assert 'href="/admin/"' not in content

    links = LinkCollector()
    links.feed(content)
    for link in links.links:
        if link.startswith("/docs/"):
            assert client.get(urlsplit(link).path, follow=True).status_code == 200, link


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/docs/deployment/environment-variables/",
        "/docs/deployment/render-deployment/",
        "/docs/getting-started/local-terminal-development/",
        "/docs/getting-started/design-system/",
        "/docs/features/example_feature/",
        "/docs/missing/page/",
        "/docs/api-reference/missing/",
    ],
)
def test_retired_and_unknown_docs_are_not_served(client, path):
    assert client.get(path).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/explore/"),
        ("get", "/explore/?saved=1"),
        ("get", "/settings"),
        ("post", "/designs/00000000-0000-0000-0000-000000000001/save/"),
        ("post", "/settings/api-key/rotate/"),
    ],
)
def test_public_docs_do_not_open_protected_website_actions(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/user"),
        ("get", "/api/v1/designs"),
        ("get", "/api/v1/designs/00000000-0000-0000-0000-000000000001"),
        ("post", "/api/v1/designs"),
    ],
)
def test_public_docs_do_not_open_authenticated_api(client, method, path):
    assert getattr(client, method)(path).status_code == 401


@pytest.mark.django_db
def test_all_public_docs_are_in_sitemap(client, settings):
    settings.SITE_URL = "https://tastefulkit.com"
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    content = response.content.decode()
    assert DOCS_PAGES
    for page in DOCS_PAGES:
        assert f"<loc>https://tastefulkit.com{page['url']}</loc>" in content
    assert "/docs/deployment/" not in content


def test_docs_navigation_uses_product_guides_and_frontmatter_titles():
    navigation = get_docs_navigation()
    assert [section["category_slug"] for section in navigation] == [
        "getting-started",
        "using-tastefulkit",
        "api-reference",
    ]
    assert navigation[0]["pages"][0]["title"] == "Start here"
    assert navigation[-1]["category"] == "API Reference"
