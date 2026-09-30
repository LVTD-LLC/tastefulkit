import pytest
from django.urls import reverse

from apps.catalogue.models import Design, SavedDesign

pytestmark = pytest.mark.django_db
GUIDE = "# Public design guide"


@pytest.fixture
def guide_design(user):
    return Design.objects.create(
        title="Free screenshot reference",
        source_url="https://example.com/",
        description="Public reference metadata",
        fingerprint="paid-guide-reference",
        submitted_by=user,
        capture_status="ready",
        screenshot="free-screenshot.png",
        thumbnail="free-thumbnail.png",
        design_markdown=GUIDE,
    )


@pytest.mark.parametrize("kind", [Design.Kind.LANDING, Design.Kind.HERO, Design.Kind.CTA])
def test_guest_can_browse_search_and_open_design(client, guide_design, kind):
    guide_design.kind = kind
    guide_design.save()
    for params in ({"kind": kind}, {"kind": kind, "q": "Free screenshot"}):
        response = client.get("/explore/", params)
        assert response.status_code == 200
        assert guide_design in response.context["page"]
        assert b"Saved references" not in response.content
    detail = client.get(guide_design.get_absolute_url())
    assert detail.status_code == 200
    assert b"free-screenshot.png" in detail.content
    assert guide_design.design_markdown.encode() in detail.content
    assert b"Sign in to save" in detail.content
    assert client.get(reverse("design_markdown", args=[guide_design.pk])).status_code == 200


def test_guest_saved_collection_and_writes_stay_private(client, guide_design, user):
    SavedDesign.objects.create(user=user, design=guide_design)
    for response in (
        client.get("/explore/?saved=1"),
        client.post(reverse("save_design", args=[guide_design.pk])),
        client.get("/rankings/?mode=personal"),
    ):
        assert response.status_code == 302
        assert "/accounts/login/" in response.url
    assert SavedDesign.objects.count() == 1
    assert client.get("/api/v1/designs").status_code == 401


@pytest.mark.parametrize("overrides", [{"published": False}, {"capture_status": "failed"}])
def test_guest_cannot_read_unavailable_designs(client, guide_design, overrides):
    for key, value in overrides.items():
        setattr(guide_design, key, value)
    guide_design.save()
    assert guide_design not in client.get("/explore/").context["page"]
    assert client.get(guide_design.get_absolute_url()).status_code == 404
    assert client.get(reverse("design_markdown", args=[guide_design.pk])).status_code == 404


@pytest.mark.parametrize(
    "path", ["/ui-libraries/", "/ai-skills/", "/docs/api-reference/introduction/", "/blog/"]
)
def test_explore_menu_destinations_are_public(client, path):
    assert client.get(path).status_code == 200
