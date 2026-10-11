"""IndexNow transport and deploy CLI; only Python's standard library is required."""

import argparse
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

ENDPOINT = "https://api.indexnow.org/indexnow"
KEY_PATH = "/indexnow-key.txt"
MAX_BYTES = 5_000_000


class IndexNowError(Exception):
    pass


def request(url, payload=None, *, exact_url=False):
    """Bound network waits and retry transient failures, never permanent errors."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "TastefulKit-IndexNow/1.0"},
    )
    for attempt in range(4):
        try:
            with urlopen(req, timeout=20) as response:
                if exact_url and response.geturl() != url:
                    raise IndexNowError("Public page redirected; snapshot incomplete")
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise IndexNowError("Response exceeds size limit")
                return response.status, body, response.headers
        except HTTPError as error:
            if error.code != 429 and error.code < 500:
                raise IndexNowError(
                    f"HTTP {error.code}; check the key and submitted URLs"
                ) from None
            retry_after = error.headers.get("Retry-After", "")
            # Long rate limits must be retried later, not ignored or shortened.
            if error.code == 429 and (not retry_after.isdigit() or int(retry_after) > 60):
                raise IndexNowError("Rate limited; retry this submission later") from None
            delay = int(retry_after) if retry_after.isdigit() else 2**attempt
        except (URLError, TimeoutError, OSError):
            delay = 2**attempt
        if attempt < 3:
            time.sleep(min(delay, 60))
    raise IndexNowError("Network request failed after four attempts")


def validate_urls(site_url, urls):
    origin = urlsplit(site_url)
    if (
        origin.scheme != "https"
        or not origin.hostname
        or origin.path
        or origin.query
        or origin.fragment
        or origin.username
    ):
        raise IndexNowError("Site URL must be a bare HTTPS origin")
    if not isinstance(urls, list) or any(not isinstance(url, str) for url in urls):
        raise IndexNowError("URL list must contain strings")
    for url in urls:
        parsed = urlsplit(url)
        if (
            parsed.scheme != origin.scheme
            or parsed.netloc != origin.netloc
            or parsed.fragment
            or parsed.query
            or any(char.isspace() or ord(char) < 32 for char in url)
        ):
            raise IndexNowError("Only canonical URLs on the configured origin may be submitted")
    return sorted(set(urls))


def sitemap_urls(site_url):
    status, body, _ = request(f"{site_url}/sitemap.xml")
    if status != 200:
        raise IndexNowError(f"Sitemap returned HTTP {status}")
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        raise IndexNowError("Invalid sitemap XML") from None
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    if root.tag != f"{ns}urlset":
        raise IndexNowError("Expected a URL sitemap, not a sitemap index")
    urls = [node.text or "" for node in root.findall(f"{ns}url/{ns}loc")]
    if not urls:
        raise IndexNowError("Refusing an empty sitemap")
    return validate_urls(site_url, urls)


def deployment_key(site_url, expected_revision=""):
    for attempt in range(30 if expected_revision else 1):
        try:
            status, body, headers = request(f"{site_url}{KEY_PATH}")
            key = body.decode("utf-8").strip()
            if status == 200 and re.fullmatch(r"[a-zA-Z0-9-]{8,128}", key):
                if (
                    not expected_revision
                    or headers.get("X-Deployment-Revision") == expected_revision
                ):
                    return key
        except (IndexNowError, UnicodeDecodeError):
            if not expected_revision:
                raise
        if attempt < 29 and expected_revision:
            time.sleep(10)
    raise IndexNowError("Live IndexNow key/revision could not be verified")


def stable_asset_url(value):
    """Ignore expiring S3 signatures, not the identity of the public asset."""
    parsed = urlsplit(value)
    if parsed.path == "/cdn-cgi/l/email-protection" and re.fullmatch(
        r"(?:[a-fA-F0-9]{2}){2,}", parsed.fragment
    ):
        # Cloudflare randomizes the XOR key on every response; hash the public identity.
        encoded = bytes.fromhex(parsed.fragment)
        return "mailto:" + bytes(value ^ encoded[0] for value in encoded[1:]).decode("utf-8")
    query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not k.lower().startswith("x-amz-")
    ]
    return urlunsplit(parsed._replace(query=urlencode(query)))


class PublicContent(HTMLParser):
    """Fingerprint editorial HTML, excluding per-request/runtime credentials."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.in_main = False
        self.saw_main = False
        self.in_title = False
        self.script = None
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "main":
            self.in_main = self.saw_main = True
        if tag == "title":
            self.in_title = True
        if tag == "script":
            self.script = attrs.get("type", "script")
        if tag == "style":
            self.in_style = True
        if tag == "meta" and (
            attrs.get("name") in {"description", "robots", "twitter:card"}
            or attrs.get("property", "").startswith("og:")
        ):
            if attrs.get("property") in {"og:image", "og:video"}:
                attrs["content"] = stable_asset_url(attrs.get("content", ""))
            self.parts.append((tag, sorted(attrs.items())))
        if tag == "link" and attrs.get("rel") == "canonical":
            self.parts.append(("canonical", attrs.get("href", "")))
        if self.in_main and not self.script and not self.in_style:
            # Form inputs, JS attributes and CSS/build hashes are not editorial content.
            selected = {
                k: stable_asset_url(v or "") if k in {"href", "src", "poster"} else v
                for k, v in attrs.items()
                if k in {"href", "src", "alt", "poster"}
            }
            if selected:
                self.parts.append((tag, sorted(selected.items())))

    def handle_endtag(self, tag):
        if tag == "main":
            self.in_main = False
        if tag == "title":
            self.in_title = False
        if tag == "script":
            self.script = None
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style or (self.script and self.script != "application/ld+json"):
            return
        if self.in_main or self.in_title or self.script == "application/ld+json":
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def fingerprint(url):
    status, body, headers = request(url, exact_url=True)
    if status != 200 or "text/html" not in headers.get("Content-Type", ""):
        raise IndexNowError("Public page is not HTML 200; snapshot incomplete")
    parser = PublicContent()
    parser.feed(body.decode("utf-8"))
    if not parser.saw_main or not parser.parts:
        raise IndexNowError("Public page has no main content; snapshot incomplete")
    return hashlib.sha256(json.dumps(parser.parts, ensure_ascii=False).encode()).hexdigest()


def snapshot(site_url):
    urls = sitemap_urls(site_url)
    # Only hashes persist. Never store page bodies, session tokens or signed asset URLs.
    with ThreadPoolExecutor(max_workers=4) as pool:
        hashes = dict(zip(urls, pool.map(fingerprint, urls), strict=True))
    # Refuse a moving/incomplete inventory rather than inventing removed URLs.
    if urls != sitemap_urls(site_url):
        raise IndexNowError("Sitemap changed during snapshot; retry later")
    return {"version": 1, "site_url": site_url, "pages": hashes}


def validate_snapshot(site_url, value):
    if (
        not isinstance(value, dict)
        or value.get("version") != 1
        or value.get("site_url") != site_url
        or not isinstance(value.get("pages"), dict)
        or not value["pages"]
    ):
        raise IndexNowError(
            "A complete version-1 content snapshot is required; URL lists cannot detect changes"
        )
    validate_urls(site_url, list(value["pages"]))
    if any(
        not isinstance(v, str) or not re.fullmatch(r"[a-f0-9]{64}", v)
        for v in value["pages"].values()
    ):
        raise IndexNowError("Invalid content fingerprint")
    return value["pages"]


def submit(site_url, previous=None, expected_revision="", dry_run=False):
    site_url = site_url.rstrip("/")
    validate_urls(site_url, [])
    before = validate_snapshot(site_url, previous)
    key = deployment_key(site_url, expected_revision)
    after = validate_snapshot(site_url, snapshot(site_url))
    # Recheck rollout identity after the crawl, before any notification.
    if expected_revision:
        deployment_key(site_url, expected_revision)
    urls = sorted(url for url in before.keys() | after.keys() if before.get(url) != after.get(url))
    if dry_run:
        return f"Dry run: {len(urls)} changed/new/removed public URLs; no submission sent"
    if not urls:
        return "No changed public URLs; no IndexNow submission sent"
    statuses = []
    for start in range(0, len(urls), 10_000):
        payload = {
            "host": urlsplit(site_url).netloc,
            "key": key,
            "keyLocation": f"{site_url}{KEY_PATH}",
            "urlList": urls[start : start + 10_000],
        }
        status, _, _ = request(ENDPOINT, payload)
        if status not in (200, 202):
            raise IndexNowError(f"Unexpected IndexNow response: HTTP {status}")
        statuses.append(status)
    pending = "; key validation pending" if 202 in statuses else ""
    return (
        f"IndexNow received {len(urls)} changed/new/removed URLs "
        f"(HTTP {', '.join(map(str, statuses))}){pending}. "
        "Indexing is not guaranteed."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", required=True)
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Save pre-deployment public content hashes, without submitting",
    )
    parser.add_argument(
        "--previous", type=Path, help="Compare with a complete pre-deployment content snapshot"
    )
    parser.add_argument("--expected-revision", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        site_url = args.site_url.rstrip("/")
        validate_urls(site_url, [])
        if args.snapshot:
            before = snapshot(site_url)
            args.snapshot.write_text(json.dumps(before), encoding="utf-8")
            print(f"Saved {len(before['pages'])} pre-deployment public content hashes")
        else:
            previous = (
                json.loads(args.previous.read_text(encoding="utf-8")) if args.previous else None
            )
            print(submit(site_url, previous, args.expected_revision, args.dry_run))
    except (IndexNowError, ValueError, OSError, UnicodeError) as error:
        parser.exit(1, f"IndexNow failed: {error}\n")


if __name__ == "__main__":
    main()
