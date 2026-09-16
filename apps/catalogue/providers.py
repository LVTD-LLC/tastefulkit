"""Source URL validation and search-time query embeddings only."""

import ipaddress
import json
import math
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

EMBEDDING_MODEL = "@cf/baai/bge-base-en-v1.5"


class RetryableProviderError(ValueError):
    def __init__(self, retry_after=60):
        super().__init__("Search embedding provider temporarily unavailable.")
        self.retry_after = retry_after


def public_url(value):
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Use a complete public HTTP or HTTPS URL.")
    if parts.username or parts.password or parts.port not in {None, 80, 443}:
        raise ValueError("Credentials and non-standard ports are not allowed in source URLs.")
    try:
        addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError) as exc:
        raise ValueError("The source hostname could not be resolved.") from exc
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Use a public Internet source URL.")
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, "")
    )


def cloudflare_request(path, payload):
    if not settings.CF_RENDER_TOKEN or not settings.CF_ACCOUNT_ID:
        raise ValueError("Search embedding provider is not configured.")
    request = Request(
        f"https://api.cloudflare.com/client/v4/accounts/{settings.CF_ACCOUNT_ID}/{path}",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {settings.CF_RENDER_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            content = response.read(20 * 1024 * 1024 + 1)
    except HTTPError as exc:
        if exc.code in {429, 502, 503, 504}:
            try:
                delay = max(60, min(86400, int(exc.headers.get("Retry-After", "60"))))
            except ValueError:
                delay = 60
            raise RetryableProviderError(delay) from None
        raise ValueError(
            f"Cloudflare returned HTTP {exc.code}; retry or check provider access."
        ) from None
    except (URLError, TimeoutError, OSError):
        raise RetryableProviderError(60) from None
    if len(content) > 20 * 1024 * 1024:
        raise ValueError("Provider response exceeded the 20 MB limit.")
    result = json.loads(content)
    if not result.get("success"):
        raise ValueError("The embedding provider could not complete this request.")
    return result["result"]


def embed(text):
    import hashlib

    key = "embedding:" + hashlib.sha256((EMBEDDING_MODEL + text).encode()).hexdigest()
    if (cached := cache.get(key)) is not None:
        return cached
    result = cloudflare_request(f"ai/run/{EMBEDDING_MODEL}", {"text": [text[:6000]]})
    vector = result["data"][0]
    if len(vector) != 768 or any(not math.isfinite(float(v)) for v in vector):
        raise ValueError("The embedding provider returned an invalid vector.")
    cache.set(key, vector, 3600)
    return vector
