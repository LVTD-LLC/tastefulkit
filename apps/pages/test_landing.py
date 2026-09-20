from uuid import UUID

import pytest

from apps.catalogue.models import Design, DesignRating, SavedDesign

pytestmark = pytest.mark.django_db


def create_design(user, number, **overrides):
    return Design.objects.create(
        submitted_by=user,
        id=UUID(int=number),
        fingerprint=str(number),
        title=f"Landing example {number}",
        source_url=f"https://example.com/{number}",
        **{
            "capture_status": Design.Status.READY,
            "screenshot": "screenshot.png",
            "thumbnail": "thumbnail.png",
            **overrides,
        },
    )


def test_homepage_matches_first_six_global_results_for_guests_and_members(client, user):
    designs = [create_design(user, number) for number in range(1, 9)]
    # Not creation order: include a tie and an unrated reference's default Elo.
    for design, score in zip(designs, [1200, 1400, 1300, 1200, 1100, 900, 800, 700], strict=True):
        DesignRating.objects.create(design_id=design.pk, score=score)
    unrated = create_design(user, 9)
    for number, overrides in enumerate(
        [
            {"published": False},
            {"capture_status": Design.Status.PENDING},
            {"capture_status": Design.Status.FAILED},
            {"screenshot": ""},
            {"thumbnail": ""},
            {"kind": Design.Kind.PRICING},
        ],
        10,
    ):
        excluded = create_design(user, number, **overrides)
        DesignRating.objects.create(design_id=excluded.pk, score=2000)
    SavedDesign.objects.create(user=user, design=designs[-1])
    expected = [designs[index] for index in [1, 2, 0, 3, 4]] + [unrated]

    for signed_in in [False, True]:
        if signed_in:
            client.force_login(user)
        response = client.get("/?mode=personal")
        assert response.status_code == 200
        assert response.context["designs"] == expected
        ranking = client.get("/rankings/")
        assert response.context["designs"] == list(ranking.context["page"])[:6]
        html = response.content.decode()
        assert html.count('class="design-card"') == 6
        assert [html.index(f">{design.title} <") for design in expected] == sorted(
            html.index(f">{design.title} <") for design in expected
        )
        assert 'href="/rankings/"' in html
        assert "no-store" in response["Cache-Control"]
        # Public teasers do not unlock the full screenshot or paid guide.
        teaser = client.get(expected[0].get_absolute_url())
        assert teaser.status_code == 200
        assert b"Explore membership" in teaser.content
        assert b"screenshot.png" not in teaser.content
        guide = client.get(expected[0].get_absolute_url() + "DESIGN.md")
        assert guide.status_code == 302
        assert guide.url == "/pricing/" if signed_in else "/accounts/login/" in guide.url


@pytest.mark.parametrize("count", [0, 2])
def test_homepage_handles_a_small_or_empty_ranking(client, user, count):
    for number in range(1, count + 1):
        create_design(user, number)
    response = client.get("/")
    assert response.status_code == 200
    assert len(response.context["designs"]) == count
    assert response.content.count(b'class="design-card"') == count
    assert (b"We're collecting the first landing pages." in response.content) == (count == 0)
