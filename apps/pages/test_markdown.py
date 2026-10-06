"""Shared response negotiation: representation, content and permission boundaries."""

from types import SimpleNamespace

import markdown
import pytest
from bs4 import BeautifulSoup
from django.http import HttpResponse, HttpResponseRedirect, StreamingHttpResponse
from django.test import RequestFactory

from tastefulkit.markdown import MarkdownMiddleware, markdown_exempt

HTML = (
    "<!doctype html><html><body><nav>Site menu</nav>"
    "<main><h1>Example</h1><p>Body.</p></main></body></html>"
)


def respond(
    accept="text/markdown", *, response=None, path="/new-public-page/", method="get", **headers
):
    request = getattr(RequestFactory(), method)(
        path, **({"HTTP_ACCEPT": accept} if accept else {}), **headers
    )
    return MarkdownMiddleware(
        lambda request: response if response is not None else HttpResponse(HTML)
    )(request)


@pytest.mark.parametrize(
    ("accept", "is_markdown"),
    [
        ("text/markdown", True),
        ("text/markdown; charset=utf-8", True),
        ("text/html;q=0.2, text/markdown;q=0.8", True),
        ("text/html", False),
        ("text/markdown;q=0, text/html", False),
        ("text/markdown;q=0.2, text/html;q=0.8", False),
        ("*/*", False),
        ("text/*", False),
        (None, False),
    ],
)
def test_new_public_pages_negotiate_by_default(accept, is_markdown):
    response = respond(accept)
    assert response.status_code == 200
    assert "Accept" in response["Vary"]
    if is_markdown:
        assert response["Content-Type"] == "text/markdown; charset=utf-8"
        assert response.content == b"# Example\n\nBody.\n"
    else:
        assert response["Content-Type"].startswith("text/html")
        assert response.content == HTML.encode()


def test_conversion_preserves_content_not_controls_or_hidden_secrets():
    html = """<html><body><header>Site chrome</header><main>
    <h1>Reference</h1><p><a href="/explore/?page=2&amp;q=warm">Next</a></p>
    <img src="/media/reference.png" alt="Reference screenshot">
    <video controls><source src="/media/preview.mp4" type="video/mp4"></video>
    <ul><li>First item</li><li>Second item</li></ul>
    <table><tr><th>Name</th><th>Price</th></tr><tr><td>Personal</td><td>$49</td></tr></table>
    <details><summary>Guide</summary><pre># Design\n\n```css\na { color: red; }\n```</pre></details>
    <script>script-secret</script><style>style-secret</style><template>template-secret</template>
    <form><input value="csrf-secret"><button>Submit</button></form>
    <textarea>textarea-secret</textarea><div hidden>hidden-secret</div>
    <span aria-hidden="true">decorative-secret</span>
    <div data-markdown-exclude>excluded-secret</div>
    <div class="ph-no-capture">private-secret</div><aside>Sidebar chrome</aside>
    <p>&lt;script&gt;literal text&lt;/script&gt;</p>
    </main><footer>Footer chrome</footer></body></html>"""
    body = respond(response=HttpResponse(html)).content.decode()
    assert body.startswith("# Reference")
    assert "[Next](/explore/?page=2&q=warm)" in body
    assert "![Reference screenshot](/media/reference.png)" in body
    assert "[Video](/media/preview.mp4)" in body
    assert "* First item" in body
    assert "| Name | Price |" in body
    assert "| Personal | $49 |" in body
    assert "secret" not in body and "chrome" not in body
    rendered = BeautifulSoup(
        markdown.markdown(body, extensions=["fenced_code", "tables"]), "html.parser"
    )
    assert rendered.find("pre").get_text().strip() == "# Design\n\n```css\na { color: red; }\n```"
    assert rendered.find("script") is None


@pytest.mark.parametrize(
    "path",
    [
        "/admin/",
        "/admin-panel",
        "/accounts/login/",
        "/settings",
        "/settings/api-key/rotate/",
        "/billing/return/",
        "/arena/",
        "/api/docs",
        "/mcp/",
    ],
)
def test_sensitive_and_protocol_routes_are_excluded(path):
    assert respond(path=path).content == HTML.encode()


def test_view_can_opt_out():
    @markdown_exempt
    def view(request):
        return HttpResponse(HTML)

    request = RequestFactory().get("/custom/", HTTP_ACCEPT="text/markdown")
    request.resolver_match = SimpleNamespace(func=view)
    assert MarkdownMiddleware(view)(request).content == HTML.encode()


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_mutations_are_unchanged(method):
    assert respond(method=method).content == HTML.encode()


@pytest.mark.parametrize("header", ["HTTP_HX_REQUEST", "HTTP_HX_HISTORY_RESTORE_REQUEST"])
def test_htmx_is_unchanged_and_varies(header):
    response = respond(**{header: "true"})
    assert response.content == HTML.encode()
    assert "HX-Request" in response["Vary"]
    assert "HX-History-Restore-Request" in response["Vary"]
    assert "HX-Request" in respond("text/html")["Vary"]


def test_non_html_redirect_download_stream_and_fragment_are_unchanged():
    responses = [
        HttpResponse('{"ok":true}', content_type="application/json"),
        HttpResponse("# Native Markdown", content_type="text/markdown"),
        HttpResponseRedirect("/accounts/login/"),
        HttpResponse(HTML, headers={"Content-Disposition": 'attachment; filename="page.html"'}),
        HttpResponse(HTML, headers={"Content-Encoding": "gzip"}),
        HttpResponse("<p>Fragment</p>"),
        HttpResponse(status=204),
        HttpResponse(HTML, status=206),
    ]
    for original in responses:
        content = original.content
        response = respond(response=original)
        assert response is original
        assert response.content == content
    stream = StreamingHttpResponse(iter([b"stream"]))
    assert respond(response=stream) is stream
    assert b"".join(stream.streaming_content) == b"stream"


def test_cache_headers_cookies_and_status_are_preserved_but_validators_rebuilt():
    original = HttpResponse(
        HTML,
        headers={
            "Vary": "Cookie",
            "Cache-Control": "private, no-store",
            "ETag": '"html"',
            "Content-Length": str(len(HTML)),
            "Content-MD5": "old",
            "Content-Digest": "old",
        },
    )
    original.set_cookie("sessionid", "test-session", httponly=True)
    response = respond(response=original)
    assert "Cookie" in response["Vary"] and "Accept" in response["Vary"]
    assert response["Cache-Control"] == "private, no-store"
    assert response.cookies["sessionid"].value == "test-session"
    assert int(response["Content-Length"]) == len(response.content)
    assert (
        "ETag" not in response
        and "Content-MD5" not in response
        and "Content-Digest" not in response
    )


def test_unsafe_urls_are_not_promoted_to_markdown_links():
    html = (
        '<main><h1>Title</h1><a href="javascript:alert(1)">Bad</a>'
        '<img src="data:text/html,bad"><a href="https://example.com">Good</a></main>'
    )
    body = respond(response=HttpResponse(html)).content.decode()
    assert "javascript:" not in body and "data:text" not in body
    assert "[Good](https://example.com)" in body


def test_size_limit_and_conversion_failure_leave_working_html(settings, monkeypatch):
    settings.MARKDOWN_MAX_HTML_BYTES = 5
    assert respond().content == HTML.encode()
    settings.MARKDOWN_MAX_HTML_BYTES = 2048
    monkeypatch.setattr("tastefulkit.markdown.html_to_markdown", lambda html: 1 / 0)
    assert respond().content == HTML.encode()


@pytest.fixture
def reference_pages(user):
    from apps.catalogue.models import AISkill, Design, UILibrary
    from apps.pages.test_landing import create_design

    design = create_design(
        user,
        1,
        description="Warm editorial layout",
        design_markdown="# Design\n\n```css\na { color: red; }\n```",
        video="preview.mp4",
        motion_notes="A gentle fade.",
    )
    library = create_design(user, 2, kind=Design.Kind.UI_LIBRARY, description="Reusable controls")
    UILibrary.objects.create(
        design=library,
        frameworks=["React", "Vue"],
        notes="Accessible primitives",
        website_url="https://example.com/ui",
        pricing=[{"name": "Personal", "billing": "one_time", "amount": "49.00", "currency": "USD"}],
    )
    skill = AISkill.objects.create(
        name="Typography skill",
        source_url="https://example.com/skill",
        description="Review typography",
        installation="npx skills add example/design",
        submitted_by=user,
    )
    return design, library, skill


@pytest.mark.django_db
@pytest.mark.parametrize("signed_in", [False, True])
def test_real_public_routes_have_markdown_without_private_keys(
    client, user, reference_pages, signed_in
):
    from apps.pages.blog import published_posts

    key = user.profile.ensure_api_key()
    if signed_in:
        client.force_login(user)
    design, library, skill = reference_pages
    routes = [
        ("/", "Find your taste"),
        ("/explore/", design.title),
        ("/rankings/", design.title),
        ("/ui-libraries/", library.title),
        ("/ai-skills/", skill.name),
        (design.get_absolute_url(), "Warm editorial layout"),
        (library.get_absolute_url(), "React Vue"),
        (skill.get_absolute_url(), "npx skills add example/design"),
        ("/how-to-use/", "How to Use TastefulKit"),
        ("/docs/getting-started/introduction/", "TastefulKit"),
        ("/blog/", "TastefulKit"),
        ("/privacy-policy", "Privacy"),
        ("/terms-of-service", "Terms"),
    ]
    posts = published_posts()
    if posts:
        routes.append((f"/blog/{posts[0].slug}/", posts[0].title))
    for path, expected in routes:
        response = client.get(path, HTTP_ACCEPT="text/markdown")
        assert response.status_code == 200, path
        assert response["Content-Type"] == "text/markdown; charset=utf-8", path
        assert "Accept" in response["Vary"]
        body = response.content.decode()
        assert expected in body, path
        assert key not in body
        assert "csrfmiddlewaretoken" not in body
        assert "<!DOCTYPE" not in body
        html = client.get(path, HTTP_ACCEPT="text/html")
        assert html["Content-Type"].startswith("text/html")
        assert b"<!DOCTYPE html>" in html.content
        assert "Accept" in html["Vary"]
    detail = client.get(design.get_absolute_url(), HTTP_ACCEPT="text/markdown").content.decode()
    assert "screenshot.png" in detail and "[Video](/media/preview.mp4)" in detail
    assert "```css" in detail


@pytest.mark.django_db
def test_homepage_ranking_parity_and_head(client, user):
    from apps.catalogue.models import DesignRating
    from apps.pages.test_landing import create_design

    for number in range(1, 9):
        design = create_design(user, number)
        DesignRating.objects.create(design_id=design.pk, score=1000 + number)
    create_design(user, 10, published=False)
    html = client.get("/", HTTP_ACCEPT="text/html")
    expected = [design.get_absolute_url() for design in html.context["designs"]]
    response = client.get("/", HTTP_ACCEPT="text/markdown")
    rendered = BeautifulSoup(markdown.markdown(response.content.decode()), "html.parser")
    assert [heading.a["href"] for heading in rendered.find_all("h3")] == expected
    head = client.head("/", HTTP_ACCEPT="text/markdown")
    assert head.status_code == 200 and head.content == b""
    assert head["Content-Type"] == response["Content-Type"]
    assert head["Content-Length"] == response["Content-Length"]


@pytest.mark.django_db
def test_filters_pagination_and_visibility_are_preserved(client, user, settings):
    from apps.pages.test_landing import create_design

    settings.QDRANT_URL = ""
    for number in range(1, 26):
        create_design(user, number, description="Velvet reference")
    hidden = create_design(user, 26, description="Velvet", published=False)
    unrelated = create_design(user, 27, description="Monochrome")
    response = client.get("/explore/?q=Velvet", HTTP_ACCEPT="text/markdown")
    body = response.content.decode()
    assert "25 designs" in body
    assert "q=Velvet&page=2" in body
    assert hidden.get_absolute_url() not in body
    assert unrelated.get_absolute_url() not in body
    second = client.get("/explore/?q=Velvet&page=2", HTTP_ACCEPT="text/markdown")
    assert "Page 2 of 2" in second.content.decode()
    assert client.get(hidden.get_absolute_url(), HTTP_ACCEPT="text/markdown").status_code == 404
    for path in ["/explore/?saved=1", "/rankings/?mode=personal"]:
        redirect = client.get(path, HTTP_ACCEPT="text/markdown")
        assert redirect.status_code == 302
        assert redirect["Location"].startswith("/accounts/login/")


@pytest.mark.django_db
def test_account_pages_and_raw_guide_stay_native(client, user, reference_pages):
    client.force_login(user)
    response = client.get("/settings", HTTP_ACCEPT="text/markdown")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    design, _, _ = reference_pages
    response = client.get(design.get_absolute_url() + "DESIGN.md", HTTP_ACCEPT="text/markdown")
    assert response.content.decode() == design.design_markdown
    assert "attachment" in response["Content-Disposition"]


def test_block_link_labels_and_adjacent_badges_remain_readable():
    html = (
        '<main><a href="/next/"><div>Next</div><div>Guide</div></a>'
        "<span>React</span><span>Vue</span></main>"
    )
    body = respond(response=HttpResponse(html)).content.decode()
    assert "[Next Guide](/next/) React Vue" in body
    rendered = BeautifulSoup(markdown.markdown(body), "html.parser")
    assert rendered.a["href"] == "/next/"
