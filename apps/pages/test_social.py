from io import BytesIO

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.template.loader import render_to_string
from django.urls import reverse
from PIL import Image

from apps.pages.social import PAGES, document_info
from apps.pages.social_images import fitted_title, render_social_image
from apps.pages.test_metadata import HeadMetadata
from apps.pages.views import get_docs_navigation, get_flat_page_list


@pytest.fixture(autouse=True)
def public_origin(settings):
    settings.SITE_URL = "https://tastefulkit.com"
    cache.clear()


@pytest.mark.parametrize("key", PAGES)
def test_public_page_metadata_is_complete_and_uses_stable_first_party_urls(key):
    from django.template import Context, Template

    html = Template("{% load social_metadata %}{% page_metadata key %}").render(
        Context({"key": key})
    )
    head = HeadMetadata()
    head.feed(html)
    assert head.tags["og:title"] == head.tags["twitter:title"]
    assert (
        head.tags["description"] == head.tags["og:description"] == head.tags["twitter:description"]
    )
    assert (
        head.tags["og:url"] == head.tags["canonical"] == ["https://tastefulkit.com" + reverse(key)]
    )
    assert head.tags["og:image"] == head.tags["twitter:image"]
    assert head.tags["og:image"][0].startswith("https://tastefulkit.com/")
    assert "?" not in head.tags["og:image"][0]
    assert head.tags["og:image:alt"] == head.tags["twitter:image:alt"]
    assert head.tags["og:image:alt"][0]
    assert head.tags["twitter:card"] == ["summary_large_image"]
    assert all(len(values) == 1 for values in head.tags.values())


@pytest.mark.parametrize("key", [key for key, page in PAGES.items() if "image" not in page])
def test_generated_page_cards_are_public_pngs(client, key):
    response = client.get(reverse("page_social_image", args=[key]))
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    with Image.open(BytesIO(response.content)) as image:
        assert image.size == (1200, 630)
        assert image.format == "PNG"
    assert client.get(reverse("page_social_image", args=[key])).content == response.content
    assert client.post(reverse("page_social_image", args=[key])).status_code == 405


@pytest.mark.parametrize(
    "doc", get_flat_page_list(get_docs_navigation()), ids=lambda doc: doc["url"]
)
def test_every_document_has_a_generated_preview(client, doc):
    category, page = doc["category_slug"], doc["page_slug"]
    title, description = document_info(category, page)
    head = HeadMetadata()
    head.feed(
        render_to_string(
            "pages/docs/docs_page.html",
            {
                "user": AnonymousUser(),
                "current_category": category,
                "current_page": page,
            },
        )
    )
    assert head.tags["canonical"] == ["https://tastefulkit.com" + doc["url"]]
    assert title in head.tags["og:title"][0]
    assert head.tags["og:description"] == [description]
    response = client.get(reverse("docs_social_image", args=[category, page]))
    assert response.status_code == 200
    with Image.open(BytesIO(response.content)) as image:
        assert image.size == (1200, 630)


@pytest.mark.parametrize(
    "path",
    [
        "/social/pages/unknown.png",
        "/social/pages/landing.png",
        "/social/docs/missing/page.png",
        "/social/docs/deployment/environment-variables.png",
        "/social/docs/../settings.png",
    ],
)
@pytest.mark.django_db
def test_unknown_or_retired_cards_are_not_generated(client, path):
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("title", ["M" * 160, "very long title " * 15, "设计参考 — تصميم — café"])
def test_titles_fit_the_card_and_unicode_renders(title):
    for width in (430, 1104):
        face, lines = fitted_title(title, width)
        assert len(lines) <= 3
        assert all(face.getlength(line) <= width for line in lines)
        assert len(lines) * (face.size + 10) <= 270
    with Image.open(BytesIO(render_social_image(title, "A reference.", "Documentation"))) as image:
        assert image.size == (1200, 630)


def test_personal_rankings_do_not_publish_social_metadata():
    head = HeadMetadata()
    head.feed(
        render_to_string("catalogue/rankings.html", {"mode": "personal", "user": AnonymousUser()})
    )
    assert head.tags["robots"] == ["noindex, nofollow"]
    assert "og:image" not in head.tags
