"""Shared header contract across marketing and signed-in page shells."""

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse


@pytest.mark.parametrize("base", ["base_landing.html", "base_app.html"])
@pytest.mark.parametrize("member", [False, True])
def test_shared_header_destinations_and_account_actions(base, member):
    username = '<script>alert("name")</script>'
    user = (
        SimpleNamespace(is_authenticated=True, get_username=lambda: username)
        if member
        else AnonymousUser()
    )
    request = RequestFactory().get("/")
    request.user = user
    html = render_to_string(
        base, {"user": user, "request": request, "csrf_token": "test-csrf-token"}
    )
    header = html.split("<header", 1)[1].split("</header>", 1)[0]
    for route in ["voting_arena", "ui_libraries", "ai_skills", "docs_home", "blog_index"]:
        assert f'href="{reverse(route)}"' in header
    assert f'href="{reverse("home")}?kind=landing_page"' in header
    assert header.index(">AI skills</a>") < header.index("<hr") < header.index(">Docs</a>")
    assert "data-theme-toggle" in header
    assert f'href="{reverse("design_rankings")}"' not in header
    if member:
        assert username not in header
        assert "&lt;script&gt;" in header
        assert f'href="{reverse("settings")}"' in header
        assert f'method="post" action="{reverse("account_logout")}"' in header
        assert 'name="csrfmiddlewaretoken"' in header
        assert 'type="submit">Log out</button>' in header
        assert f'href="{reverse("account_login")}"' not in header
    else:
        assert "Log out" not in header
        assert f'href="{reverse("settings")}"' not in header
        assert f'href="{reverse("account_login")}"' in header
        assert f'href="{reverse("account_signup")}"' in header
