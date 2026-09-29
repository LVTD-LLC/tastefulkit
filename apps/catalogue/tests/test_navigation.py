from uuid import uuid4

import pytest

from apps.catalogue.models import Design

pytestmark = pytest.mark.django_db


@pytest.fixture
def components(user):
    return [
        Design.objects.create(
            title=f"{kind} {i}",
            kind=kind,
            fingerprint=str(uuid4()),
            submitted_by=user,
            capture_status="ready",
            screenshot="shot.png",
            thumbnail="thumb.png",
        )
        for kind in ("landing_page", "hero", "cta")
        for i in range(2)
    ]


@pytest.mark.parametrize(
    "url",
    [
        "/explore/?kind=hero",
        "/arena/?kind=hero",
        "/rankings/?kind=hero",
        "/rankings/?mode=personal&kind=hero",
    ],
)
def test_shared_navigation_and_scoped_results(client, user, components, url):
    client.force_login(user)
    response = client.get(url)
    assert response.status_code == 200
    html = response.content.decode()
    assert 'aria-label="Content types"' in html
    assert '<select name="kind"' not in html
    for href in (
        "/explore/?kind=hero",
        "/arena/?kind=hero",
        "/rankings/?kind=hero",
        "/rankings/?mode=personal&amp;kind=hero",
    ):
        assert f'href="{href}"' in html
    items = response.context.get("pair") or response.context.get("page")
    assert items and all(d.kind == "hero" for d in items)


def test_guest_personal_link_preserves_kind(client, components):
    response = client.get("/rankings/?kind=cta")
    assert b'href="/rankings/?mode=personal&amp;kind=cta"' in response.content
    login = client.get("/rankings/?mode=personal&kind=cta")
    assert login.status_code == 302
    assert "kind%3Dcta" in login.url


def test_directory_navigation_and_default_explore(client, user, components):
    response = client.get("/ui-libraries/")
    assert b'aria-label="Content types"' in response.content
    assert b"/arena/?kind=ui_library" in response.content
    client.force_login(user)
    response = client.get("/explore/")
    assert all(d.kind == "landing_page" for d in response.context["page"])


def test_component_vote_redirect_stays_in_type(client, components):
    response = client.get("/arena/?kind=cta")
    pair = response.context["pair"]
    assert pair and all(d.kind == "cta" for d in pair)
    result = client.post(
        "/arena/vote/",
        {"kind": "cta", "token": response.context["token"], "choice": str(pair[0].pk)},
    )
    assert result.url == "/arena/?kind=cta"
