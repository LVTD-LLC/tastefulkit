import pytest

pytestmark = pytest.mark.django_db


def payload(**changes):
    return {
        "name": "Interface review",
        "source_url": "https://github.com/example/skills/blob/main/interface/SKILL.md",
        "description": "Review interface hierarchy and accessibility.",
        "notes": "Use after implementing a screen.",
        "installation": "npx skills add example/skills",
        "compatible_agents": ["Claude Code", "Codex"],
        "tags": ["accessibility"],
        "license": "MIT",
        **changes,
    }


def submit(client, key, **changes):
    return client.post(
        "/api/v1/ai-skills", payload(**changes), content_type="application/json", HTTP_X_API_KEY=key
    )


def test_skill_ingestion_browsing_and_moderation(client, user):
    key = user.profile.rotate_api_key()
    assert submit(client, key).status_code == 401
    user.is_superuser = True
    user.save()
    response = submit(client, key)
    assert response.status_code == 201, response.content
    item = response.json()
    assert submit(client, key, name="Ignored retry").json()["name"] == "Interface review"
    assert client.get(item["url"]).status_code == 200
    assert item["url"] in client.get("/sitemap.xml").content.decode()
    assert client.get("/ai-skills/?q=codex").context["page"].paginator.count == 1
    assert client.get("/ai-skills/?q=missing").context["page"].paginator.count == 0
    assert client.get("/api/v1/ai-skills").status_code == 401
    assert client.get("/api/v1/ai-skills", HTTP_X_API_KEY=key).json()["total"] == 1
    assert "post" not in client.get("/api/openapi.json").json()["paths"]["/api/v1/ai-skills"]
    from apps.catalogue.models import AISkill

    skill = AISkill.objects.get()
    skill.published = False
    skill.save()
    assert (
        submit(client, key, replace_existing=True, name="Updated skill").json()["name"]
        == "Updated skill"
    )
    skill.refresh_from_db()
    assert not skill.published
    assert client.get(item["url"]).status_code == 404
    assert client.get("/api/v1/ai-skills/" + item["id"], HTTP_X_API_KEY=key).status_code == 404
    assert item["url"] not in client.get("/sitemap.xml").content.decode()


@pytest.mark.parametrize(
    "changes",
    [
        {"source_url": "javascript:alert(1)"},
        {"source_url": "https://user:pass@example.com/skill"},
        {"name": "  "},
        {"compatible_agents": [""]},
        {"unexpected": True},
    ],
)
def test_skill_validation(client, user, changes):
    user.is_superuser = True
    user.save()
    assert submit(client, user.profile.rotate_api_key(), **changes).status_code == 422


def test_skill_content_escaped_and_never_executed(client, user):
    user.is_superuser = True
    user.save()
    item = submit(
        client,
        user.profile.rotate_api_key(),
        notes="<script>alert(1)</script>",
        installation="echo <unsafe>",
    ).json()
    html = client.get(item["url"]).content.decode()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html and "echo &lt;unsafe&gt;" in html


def test_nonvisual_navigation(client):
    for path in ["/ui-libraries/", "/ai-skills/"]:
        response = client.get(path)
        assert response.status_code == 200
        assert b"/ai-skills/" in response.content
        assert b"/arena/?kind=ui_library" not in response.content
        assert b"/arena/?kind=ai_skill" not in response.content
    for path in ["/arena/?kind=ui_library", "/rankings/?kind=ui_library"]:
        assert client.get(path).url == "/ui-libraries/"
    assert client.get("/arena/?kind=ai_skill").url == "/ai-skills/"


@pytest.mark.parametrize("staff,superuser,active", [(True, False, True), (True, True, False)])
def test_skill_write_requires_active_superuser(client, user, staff, superuser, active):
    key = user.profile.rotate_api_key()
    user.is_staff, user.is_superuser, user.is_active = staff, superuser, active
    user.save()
    assert submit(client, key).status_code == 401
    from apps.catalogue.models import AISkill

    assert not AISkill.objects.exists()


def test_skill_source_identity_and_read_payload(client, user):
    user.is_superuser = True
    user.save()
    key = user.profile.rotate_api_key()
    original = submit(client, key).json()
    retry = submit(client, key, source_url=payload()["source_url"] + "#instructions")
    assert retry.status_code == 200
    assert retry.json()["id"] == original["id"]
    other = submit(
        client, key, source_url=payload()["source_url"].replace("/interface/", "/typography/")
    )
    assert other.status_code == 201 and other.json()["id"] != original["id"]
    read = client.get("/api/v1/ai-skills/" + original["id"], HTTP_AUTHORIZATION="Bearer " + key)
    assert read.status_code == 200 and read.json() == original
    assert client.get("/api/v1/ai-skills/not-a-uuid", HTTP_X_API_KEY=key).status_code == 422
