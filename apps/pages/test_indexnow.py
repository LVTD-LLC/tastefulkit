import hashlib
import io
import json
import re
from urllib.error import HTTPError, URLError

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from apps.pages import indexnow

SITE = "https://tastefulkit.com"
KEY = "a" * 64


class Response(io.BytesIO):
    def __init__(self, body=b"", status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = headers or {}

    def geturl(self):
        return self.url


def page_html(url):
    return f"<html><title>Public page</title><main><h1>{url}</h1></main></html>".encode()


def before_snapshot(urls):
    pages = {}
    for url in urls:
        parser = indexnow.PublicContent()
        parser.feed(page_html(url).decode())
        pages[url] = hashlib.sha256(
            json.dumps(parser.parts, ensure_ascii=False).encode()
        ).hexdigest()
    return {"version": 1, "site_url": SITE, "pages": pages}


def changed_baseline():
    return {"version": 1, "site_url": SITE, "pages": {SITE + "/old/": "a" * 64}}


def transport(monkeypatch, urls, statuses=(200,), revisions=("new",)):
    posts = []
    codes = iter(statuses)
    deployed = iter(revisions)
    xml = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    xml += "".join(f"<url><loc>{url}</loc></url>" for url in urls) + "</urlset>"

    def send(req, timeout):
        assert timeout > 0
        if req.full_url == SITE + indexnow.KEY_PATH:
            return Response(KEY.encode(), headers={"X-Deployment-Revision": next(deployed)})
        if req.full_url == SITE + "/sitemap.xml":
            return Response(xml.encode())
        if req.full_url in urls:
            result = Response(page_html(req.full_url), headers={"Content-Type": "text/html"})
            result.url = req.full_url
            return result
        assert req.full_url == indexnow.ENDPOINT
        posts.append(json.loads(req.data))
        code = next(codes)
        if code >= 400:
            raise HTTPError(req.full_url, code, "failure", {}, None)
        return Response(status=code)

    monkeypatch.setattr(indexnow, "urlopen", send)
    monkeypatch.setattr(indexnow.time, "sleep", lambda _: None)
    return posts


@override_settings(SITE_URL=SITE, SECRET_KEY="test-only", DEPLOYMENT_REVISION="new")
def test_public_key_route_and_rotation(client, settings):
    response = client.get(reverse("indexnow_key"))
    assert response.status_code == 200
    assert re.fullmatch(rb"[a-f0-9]{64}", response.content)
    assert response["Content-Type"] == "text/plain; charset=utf-8"
    assert response["Cache-Control"] == "no-store"
    assert response["X-Deployment-Revision"] == "new"
    assert client.get(reverse("indexnow_key")).content == response.content
    settings.SECRET_KEY = "rotated-test-only"
    assert client.get(reverse("indexnow_key")).content != response.content


@pytest.mark.parametrize("status", [200, 202])
@override_settings(SITE_URL=SITE)
def test_command_submits_current_and_removed_urls(monkeypatch, tmp_path, status):
    posts = transport(monkeypatch, [SITE + "/", SITE + "/docs/new/"], statuses=(status,))
    previous = tmp_path / "before.json"
    previous.write_text(json.dumps(before_snapshot([SITE + "/", SITE + "/docs/removed/"])))
    output = io.StringIO()
    call_command("submit_indexnow", previous=previous, stdout=output)
    assert posts == [
        {
            "host": "tastefulkit.com",
            "key": KEY,
            "keyLocation": SITE + indexnow.KEY_PATH,
            "urlList": [SITE + "/docs/new/", SITE + "/docs/removed/"],
        }
    ]
    assert ("validation pending" in output.getvalue()) == (status == 202)


def test_revision_wait_dry_run_and_protocol_batch_limit(monkeypatch):
    urls = [f"{SITE}/docs/{i}/" for i in range(10_001)]
    posts = transport(
        monkeypatch, urls, statuses=(200, 202), revisions=("old", "new", "new", "new", "new")
    )
    assert "Dry run" in indexnow.submit(
        SITE, before_snapshot([urls[0]]), expected_revision="new", dry_run=True
    )
    assert not posts
    indexnow.submit(SITE, changed_baseline(), expected_revision="new")
    assert [len(post["urlList"]) for post in posts] == [10_000, 2]


@pytest.mark.parametrize(
    "url",
    [
        "https://other.test/",
        SITE + "/?token=private",
        SITE + "/#part",
        "http://tastefulkit.com/",
        SITE + "/bad\npath",
    ],
)
def test_invalid_sitemap_never_submits(monkeypatch, url):
    posts = transport(monkeypatch, [url])
    with pytest.raises(indexnow.IndexNowError):
        indexnow.submit(SITE, changed_baseline())
    assert not posts


@pytest.mark.parametrize("status", [400, 403, 422, 429])
def test_permanent_or_unspecified_rate_limit_stops(monkeypatch, status):
    posts = transport(monkeypatch, [SITE + "/"], statuses=(status,))
    with pytest.raises(indexnow.IndexNowError):
        indexnow.submit(SITE, changed_baseline())
    assert len(posts) == 1


def test_transient_failure_retries_and_exhaustion_is_visible(monkeypatch):
    posts = transport(monkeypatch, [SITE + "/"], statuses=(503, 200))
    assert "HTTP 200" in indexnow.submit(SITE, changed_baseline())
    assert len(posts) == 2
    attempts = []

    def unavailable(req, timeout):
        attempts.append(req)
        raise URLError("offline")

    monkeypatch.setattr(indexnow, "urlopen", unavailable)
    with pytest.raises(indexnow.IndexNowError, match="four attempts"):
        indexnow.submit(SITE, changed_baseline())
    assert len(attempts) == 4


def test_snapshot_cli_is_read_only(monkeypatch, tmp_path):
    posts = transport(monkeypatch, [SITE + "/"])
    snapshot = tmp_path / "before.json"
    monkeypatch.setattr("sys.argv", ["indexnow", "--site-url", SITE, "--snapshot", str(snapshot)])
    indexnow.main()
    assert json.loads(snapshot.read_text()) == before_snapshot([SITE + "/"])
    assert not posts


def test_unfinished_rollout_never_submits(monkeypatch):
    posts = transport(monkeypatch, [SITE + "/"], revisions=("old",) * 30)
    with pytest.raises(indexnow.IndexNowError, match="revision"):
        indexnow.submit(SITE, changed_baseline(), expected_revision="new")
    assert not posts


def test_short_rate_limit_respects_retry_after(monkeypatch):
    responses = iter(
        [HTTPError(indexnow.ENDPOINT, 429, "rate limit", {"Retry-After": "12"}, None), Response()]
    )
    delays = []

    def send(req, timeout):
        result = next(responses)
        if isinstance(result, HTTPError):
            raise result
        return result

    monkeypatch.setattr(indexnow, "urlopen", send)
    monkeypatch.setattr(indexnow.time, "sleep", delays.append)
    assert indexnow.request(indexnow.ENDPOINT, {"urlList": [SITE + "/"]})[0] == 200
    assert delays == [12]


def test_unchanged_snapshot_never_posts(monkeypatch):
    posts = transport(monkeypatch, [SITE + "/"])
    assert "No changed" in indexnow.submit(SITE, before_snapshot([SITE + "/"]))
    assert posts == []


def test_existing_page_change_is_submitted(monkeypatch):
    posts = transport(monkeypatch, [SITE + "/", SITE + "/docs/"])
    before = before_snapshot([SITE + "/", SITE + "/docs/"])
    before["pages"][SITE + "/docs/"] = "0" * 64
    indexnow.submit(SITE, before)
    assert posts[0]["urlList"] == [SITE + "/docs/"]


@pytest.mark.parametrize(
    "previous",
    [
        None,
        [],
        [SITE + "/"],
        {},
        {"version": 1, "site_url": SITE, "pages": {}},
        {"version": 1, "site_url": "https://other.test", "pages": {SITE + "/": "a" * 64}},
        {"version": 1, "site_url": SITE, "pages": {SITE + "/": "bad"}},
    ],
)
def test_missing_or_legacy_baseline_fails_without_network(monkeypatch, previous):
    def unexpected(*args, **kwargs):
        pytest.fail("Invalid baseline must fail before network calls")

    monkeypatch.setattr(indexnow, "request", unexpected)
    with pytest.raises(indexnow.IndexNowError):
        indexnow.submit(SITE, previous)


def test_fingerprints_ignore_runtime_noise_but_detect_editorial_changes(monkeypatch):
    def markup(token, text="Useful guide", title="Title", image="a.png", link="/docs/"):
        return f'''<html><title>{title}</title>
        <meta name="description" content="A useful description">
        <meta name="sentry-trace" content="{token}">
        <meta property="og:image" content="https://assets.test/{image}?X-Amz-Signature={token}">
        <script>const csrf = "{token}"</script><main><h1>{text}</h1>
        <input name="csrfmiddlewaretoken" value="{token}">
        <img src="https://assets.test/{image}?X-Amz-Signature={token}&amp;width=600" alt="Preview">
        <a href="{link}">Docs</a></main></html>'''.encode()

    body = markup("first")
    monkeypatch.setattr(
        indexnow, "request", lambda *a, **kw: (200, body, {"Content-Type": "text/html"})
    )
    original = indexnow.fingerprint(SITE + "/")
    body = markup("second")
    assert indexnow.fingerprint(SITE + "/") == original
    for change in (
        {"text": "Revised guide"},
        {"title": "New title"},
        {"image": "b.png"},
        {"link": "/blog/"},
    ):
        body = markup("second", **change)
        assert indexnow.fingerprint(SITE + "/") != original


@pytest.mark.parametrize(
    "body,content_type", [(b"<html>Error</html>", "text/html"), (b"{}", "application/json")]
)
def test_incomplete_snapshot_fails_without_posting(monkeypatch, body, content_type):
    posts = []

    def send(url, payload=None, **kwargs):
        if payload is not None:
            posts.append(payload)
        return 200, body, {"Content-Type": content_type}

    monkeypatch.setattr(indexnow, "request", send)
    monkeypatch.setattr(indexnow, "sitemap_urls", lambda _: [SITE + "/"])
    with pytest.raises(indexnow.IndexNowError):
        indexnow.snapshot(SITE)
    assert not posts


def test_redirect_is_not_a_successful_fingerprint(monkeypatch):
    response = Response(page_html(SITE), headers={"Content-Type": "text/html"})
    response.url = SITE + "/login/"
    monkeypatch.setattr(indexnow, "urlopen", lambda *a, **kw: response)
    with pytest.raises(indexnow.IndexNowError, match="redirected"):
        indexnow.fingerprint(SITE + "/")


def test_moving_inventory_does_not_write_snapshot(monkeypatch, tmp_path):
    inventories = iter([[SITE + "/"], [SITE + "/", SITE + "/new/"]])
    monkeypatch.setattr(indexnow, "sitemap_urls", lambda _: next(inventories))
    monkeypatch.setattr(indexnow, "fingerprint", lambda _: "a" * 64)
    path = tmp_path / "before.json"
    monkeypatch.setattr("sys.argv", ["indexnow", "--site-url", SITE, "--snapshot", str(path)])
    with pytest.raises(SystemExit):
        indexnow.main()
    assert not path.exists()


def test_cloudflare_email_mask_preserves_identity_not_random_key():
    def masked(address, key):
        encoded = bytes([key]) + bytes(value ^ key for value in address.encode())
        return "/cdn-cgi/l/email-protection#" + encoded.hex()

    first = indexnow.stable_asset_url(masked("hello@example.test", 19))
    assert first == indexnow.stable_asset_url(masked("hello@example.test", 41))
    assert first != indexnow.stable_asset_url(masked("other@example.test", 41))
