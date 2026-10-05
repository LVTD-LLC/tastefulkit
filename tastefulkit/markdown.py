"""Opt-out Markdown negotiation for rendered public HTML, without fetching URLs."""

import logging
import re
from urllib.parse import quote, urlsplit

from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.utils.cache import patch_vary_headers
from markdownify import MarkdownConverter

logger = logging.getLogger(__name__)
HTML_TYPE = "text/html; charset=utf-8"
MARKDOWN_TYPE = "text/markdown; charset=utf-8"
VARY_HEADERS = ("Accept", "HX-Request", "HX-History-Restore-Request")
REMOVE_SELECTOR = (
    "script, style, template, noscript, svg, canvas, iframe, object, embed, aside, "
    "form, input, textarea, select, button, [hidden], [aria-hidden='true'], "
    "[data-markdown-exclude], .ph-no-capture"
)


def markdown_exempt(view):
    """Opt a view out; for class-based views decorate the as_view() callable."""
    view.markdown_exempt = True
    return view


def _excluded(request):
    path = request.path_info.rstrip("/")
    if any(
        path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/")
        for prefix in settings.MARKDOWN_EXCLUDED_PATH_PREFIXES
    ):
        return True
    match = getattr(request, "resolver_match", None)
    return bool(match and getattr(match.func, "markdown_exempt", False))


def _eligible(request, response):
    return (
        request.method in {"GET", "HEAD"}
        and response.status_code == 200
        and not response.streaming
        and response.get("Content-Type", "").split(";", 1)[0].lower() == "text/html"
        and "Content-Disposition" not in response
        and "Content-Encoding" not in response
        and not _excluded(request)
    )


class PageConverter(MarkdownConverter):
    @staticmethod
    def _separate_inline_items(el, text):
        # Flex/grid link and badge groups often have no source whitespace.
        sibling = el.next_sibling
        if isinstance(sibling, Tag) and sibling.name in {"a", "span"}:
            return text + " "
        return text

    def convert_a(self, el, text, parent_tags):
        # Cards/docs navigation may put block elements inside links. Blank lines
        # inside a Markdown link label would break the link entirely.
        text = super().convert_a(el, " ".join(text.split()), parent_tags)
        return self._separate_inline_items(el, text)

    def convert_span(self, el, text, parent_tags):
        return self._separate_inline_items(el, text)

    def process_text(self, el, parent_tags=None):
        text = super().process_text(el, parent_tags)
        if not {"pre", "code"}.intersection(parent_tags or ()):
            # Escaped HTML in user-authored titles must stay literal Markdown text.
            text = text.replace("<", "&lt;").replace(">", "&gt;")
        return text

    def convert_pre(self, el, text, parent_tags):
        # DESIGN.md often contains triple backticks. Choose a longer outer fence.
        code = el.get_text().strip("\n")
        fence = "`" * max(3, max((len(run) + 1 for run in re.findall(r"`+", code)), default=3))
        return f"\n\n{fence}\n{code}\n{fence}\n\n"

    def convert_video(self, el, text, parent_tags):
        source = el.get("src") or el.get("data-src")
        if not source:
            child = el.find("source", src=True)
            source = child.get("src") if child else None
        return f"\n\n[Video]({source})\n\n" if source else text


def _clean_urls(root):
    for element in root.find_all(["a", "img", "video", "source"]):
        for attribute in ("href", "src", "data-src"):
            value = element.get(attribute)
            if not value:
                continue
            try:
                safe = urlsplit(value).scheme.lower() in {"", "http", "https", "mailto"}
            except ValueError:
                safe = False
            if safe:
                element[attribute] = quote(value, safe="/:?#[]@!$&'*+,;=%~_-")
            else:
                del element[attribute]


def html_to_markdown(html):
    soup = BeautifulSoup(html, "html.parser")
    root = soup.find("main")
    # A full content document is required; never reinterpret HTMX fragments.
    if root is None or root.has_attr("data-markdown-exclude"):
        return None
    for element in root.select(REMOVE_SELECTOR):
        element.decompose()
    _clean_urls(root)
    body = PageConverter(
        heading_style="ATX", bullets="*", escape_misc=True, autolinks=False
    ).convert_soup(root)
    return body.strip() + "\n" if body.strip() else None


class MarkdownMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not _eligible(request, response):
            return response
        # Vary on HTML too, including when HTMX requests deliberately stay HTML.
        patch_vary_headers(response, VARY_HEADERS)
        if any(request.headers.get(header) == "true" for header in VARY_HEADERS[1:]):
            return response
        if request.get_preferred_type([HTML_TYPE, MARKDOWN_TYPE]) != MARKDOWN_TYPE:
            return response
        if len(response.content) > settings.MARKDOWN_MAX_HTML_BYTES:
            return response
        try:
            body = html_to_markdown(response.content.decode(response.charset))
        except Exception as error:
            # Preserve a working HTML page on conversion failure; don't log content.
            logger.warning(
                "page.markdown.conversion.failed",
                extra={
                    "event.name": "page.markdown.conversion.failed",
                    "outcome": "failure",
                    "error.type": type(error).__name__,
                },
            )
            return response
        if body is not None:
            response.charset = "utf-8"
            response.content = body
            response["Content-Type"] = MARKDOWN_TYPE
            for header in ("ETag", "Content-MD5", "Digest", "Content-Digest", "Repr-Digest"):
                if header in response:
                    del response[header]
            if "Content-Length" in response:
                response["Content-Length"] = str(len(response.content))
        return response
