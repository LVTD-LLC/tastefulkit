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


def metrics(**changes):
    return {
        "github_stars": 123,
        "github_stars_checked_at": "2026-09-30T09:00:00Z",
        "skills_sh_url": "https://skills.sh/example/skills/interface",
        "skills_sh_installs": 42,
        "skills_sh_installs_checked_at": "2026-09-30T09:00:00Z",
        **changes,
    }


def test_metrics_roundtrip_refresh_and_permissions(client, user):
    user.is_superuser = True
    user.save()
    key = user.profile.rotate_api_key()
    item = submit(
        client, key, repository_url="https://github.com/example/skills", **metrics()
    ).json()
    assert item["github_stars"] == 123 and item["skills_sh_installs"] == 42
    path = f"/api/v1/ai-skills/{item['id']}/metrics"
    assert client.patch(path, metrics(), content_type="application/json").status_code == 401
    user.is_superuser = False
    user.save()
    assert (
        client.patch(
            path, metrics(), content_type="application/json", HTTP_X_API_KEY=key
        ).status_code
        == 401
    )
    user.is_superuser = True
    user.save()
    from apps.catalogue.models import AISkill

    AISkill.objects.filter(pk=item["id"]).update(published=False, notes="Keep editorial changes")
    response = client.patch(
        path, metrics(github_stars=0), content_type="application/json", HTTP_X_API_KEY=key
    )
    assert response.status_code == 200
    assert response.json()["github_stars"] == 0
    assert response.json()["notes"] == "Keep editorial changes"
    assert not AISkill.objects.get(pk=item["id"]).published
    assert client.get(item["url"]).status_code == 404
    assert path not in client.get("/api/openapi.json").json()["paths"]


@pytest.mark.parametrize(
    "changes",
    [
        {"github_stars": -1},
        {"github_stars": 1.5},
        {"github_stars": True},
        {"github_stars": 9223372036854775808},
        {"github_stars_checked_at": None},
        {"github_stars_checked_at": "2026-09-30T09:00:00"},
        {"skills_sh_installs": -1},
        {"skills_sh_installs": "42"},
        {"skills_sh_installs_checked_at": None},
        {"skills_sh_url": ""},
        {"skills_sh_url": "https://skills.sh.evil.example/a/b/c"},
        {"skills_sh_url": "https://user@skills.sh/a/b/c"},
        {"skills_sh_url": "https://skills.sh/a/b/c?tracking=yes"},
        {"repository_url": "https://example.com/repo"},
    ],
)
def test_metric_validation(client, user, changes):
    user.is_superuser = True
    user.save()
    data = {"repository_url": "https://github.com/example/skills", **metrics(), **changes}
    assert submit(client, user.profile.rotate_api_key(), **data).status_code == 422


def test_skill_metric_sorting_search_and_unknowns(client, user):
    from apps.catalogue.models import AISkill

    key = user.profile.rotate_api_key()
    common = {"description": "Interface design", "submitted_by": user}
    for name, stars, installs in [
        ("Unknown", None, None),
        ("Zero", 0, 0),
        ("Alpha", 10, 30),
        ("Beta", 20, 20),
        ("Hidden", 999, 999),
    ]:
        values = metrics(github_stars=stars, skills_sh_installs=installs)
        if stars is None:
            values["github_stars_checked_at"] = values["skills_sh_installs_checked_at"] = None
        AISkill.objects.create(
            name=name,
            source_url=f"https://example.com/{name}",
            repository_url="https://github.com/example/skills",
            published=name != "Hidden",
            **common,
            **values,
        )
    for sort, expected in [
        ("stars", ["Beta", "Alpha", "Zero", "Unknown"]),
        ("installs", ["Alpha", "Beta", "Zero", "Unknown"]),
    ]:
        response = client.get("/ai-skills/", {"sort": sort, "q": "design"})
        assert [s.name for s in response.context["page"]] == expected
        api = client.get("/api/v1/ai-skills", {"sort": sort, "q": "design"}, HTTP_X_API_KEY=key)
        assert [s["name"] for s in api.json()["items"]] == expected
        assert b"0 GitHub stars" in response.content
        assert b"0 skills.sh installs" in response.content
        assert b"not checked" in response.content
    assert client.get("/api/v1/ai-skills?sort=bogus", HTTP_X_API_KEY=key).status_code == 422
    assert client.get("/ai-skills/?sort=bogus").context["sort"] == "name"
    for n in range(25):
        AISkill.objects.create(
            name=f"More {n}", source_url=f"https://example.com/more{n}", **common
        )
    response = client.get("/ai-skills/?q=design&sort=stars")
    assert b"sort=stars&page=2" in response.content
