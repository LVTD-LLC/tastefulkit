from io import BytesIO
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.urls import reverse
from PIL import Image

from apps.catalogue.models import Design
from apps.pages.test_metadata import HeadMetadata

pytestmark = pytest.mark.django_db


@pytest.fixture
def social_design(user):
    cache.clear()
    design = Design.objects.create(
        title='Example "design" <tag>',
        source_url="https://private-source.example/",
        description="Private full description",
        fingerprint=str(uuid4()),
        submitted_by=user,
        capture_status="ready",
        screenshot="private-full-screenshot.png",
        design_markdown="# Private design guide",
    )
    output = BytesIO()
    Image.new("RGB", (864, 600), "#102938").save(output, format="PNG")
    design.thumbnail.save("social-test.png", ContentFile(output.getvalue()))
    yield design
    design.thumbnail.delete(save=False)


@pytest.mark.parametrize("reader", ["anonymous", "unpaid", "paid"])
def test_design_sharing_requires_only_a_free_account(
    client, social_design, user, grant_membership, reader, settings
):
    settings.SITE_URL = "https://tastefulkit.com"
    if reader != "anonymous":
        client.force_login(user)
    if reader == "paid":
        grant_membership(user)
    response = client.get(social_design.get_absolute_url())
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]
    html = response.content.decode()
    head = HeadMetadata()
    head.feed(html)
    assert head.tags["og:title"] == [f"{social_design.title} | TastefulKit"]
    assert head.tags["og:image"] == [
        "https://tastefulkit.com" + reverse("design_social_image", args=[social_design.pk])
    ]
    if reader != "anonymous":
        guide = client.get(reverse("design_markdown", args=[social_design.pk]))
        if reader == "paid":
            assert guide.status_code == 200
            assert "Private design guide" in html
        else:
            assert guide.url == "/pricing/"
            assert "Private design guide" not in html
            assert "Unlock design guides" in html
        assert client.post(reverse("save_design", args=[social_design.pk])).status_code == 302
        assert "private-full-screenshot.png" in html
    else:
        assert "Create free account" in html
        assert social_design.thumbnail.url in html
        for secret in (
            "Private design guide",
            "private-full-screenshot.png",
            "Private full description",
            "private-source.example",
        ):
            assert secret not in html
        assert client.get(reverse("design_markdown", args=[social_design.pk])).status_code == 302
        assert client.post(reverse("save_design", args=[social_design.pk])).status_code == 302


def test_design_card_is_public_and_cache_cannot_bypass_visibility(client, social_design):
    url = reverse("design_social_image", args=[social_design.pk])
    first = client.get(url)
    assert first.status_code == 200 and "no-store" in first["Cache-Control"]
    assert first["Content-Type"] == "image/png"
    with Image.open(BytesIO(first.content)) as image:
        assert image.size == (1200, 630)
        assert image.getpixel((800, 300)) == (16, 41, 56)
    assert client.get(url).content == first.content
    social_design.title = "A new title"
    social_design.save()
    assert client.get(url).content != first.content
    social_design.published = False
    social_design.save()
    assert client.get(url).status_code == 404
    assert client.get(social_design.get_absolute_url()).status_code == 404
    social_design.published = True
    social_design.capture_status = "failed"
    social_design.save()
    assert client.get(url).status_code == 404
    assert client.get(social_design.get_absolute_url()).status_code == 404
    social_design.delete()
    assert client.get(url).status_code == 404


def test_missing_thumbnail_has_a_branded_fallback(client, social_design):
    social_design.thumbnail.delete()
    response = client.get(reverse("design_social_image", args=[social_design.pk]))
    assert response.status_code == 200
    with Image.open(BytesIO(response.content)) as image:
        assert image.size == (1200, 630)
    assert client.get(social_design.get_absolute_url()).status_code == 200


def test_replaced_thumbnail_refreshes_cached_card(client, social_design):
    url = reverse("design_social_image", args=[social_design.pk])
    first = client.get(url)
    social_design.thumbnail.delete(save=False)
    output = BytesIO()
    Image.new("RGB", (864, 600), "#ee5522").save(output, format="PNG")
    social_design.thumbnail.save("replacement.png", ContentFile(output.getvalue()))
    response = client.get(url)
    assert response.content != first.content
    with Image.open(BytesIO(response.content)) as image:
        assert image.getpixel((800, 300)) == (238, 85, 34)


@pytest.mark.parametrize("content", [b"invalid image", b"x" * (2 * 1024 * 1024 + 1)])
def test_unreadable_thumbnail_returns_png_without_leaking_content(client, social_design, content):
    social_design.thumbnail.delete(save=False)
    social_design.thumbnail.save("broken.png", ContentFile(content))
    response = client.get(reverse("design_social_image", args=[social_design.pk]))
    assert response.status_code == 200
    with Image.open(BytesIO(response.content)) as image:
        assert image.size == (1200, 630)


def test_nonlanding_designs_are_not_public_teasers(client, social_design):
    social_design.kind = Design.Kind.HERO
    social_design.save()
    assert client.get(social_design.get_absolute_url()).status_code == 404
    assert client.get(reverse("design_social_image", args=[social_design.pk])).status_code == 404
