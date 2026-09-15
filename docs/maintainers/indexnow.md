# IndexNow

TastefulKit submits only canonical public sitemap URLs, not authenticated
catalogue/search/account URLs. The initial deployment submits the existing
sitemap. Subsequent successful deployments resubmit the small public sitemap
(currently landing/legal/docs pages) plus its pre-deployment snapshot, so changed,
added and removed pages are all reported. This deliberately resubmits unchanged
public pages too. Database catalogue edits do not submit notifications because
those pages are not indexable or in the sitemap.

`/indexnow-key.txt` serves an IndexNow verification value with a root-level
`keyLocation`, as supported by the [protocol](https://www.indexnow.org/documentation).
It uses a domain-separated SHA-256 HMAC of the canonical site origin with Django's
existing `SECRET_KEY`. No additional credentials are required, and the secret
itself is never exposed. Rotating `SECRET_KEY` or changing `SITE_URL` changes the
verification value; the next submission reads the current value. The endpoint
is not cached and returns `X-Robots-Tag: noindex`.

## Deployment and verification

The deploy workflow retains `indexnow-before-<sha>` as an Actions artifact for
90 days before changing the live app. After both server and worker deployment
steps succeed, it waits for the key endpoint's `X-Deployment-Revision` header to
match the image's build revision, then submits to `https://api.indexnow.org/indexnow`.
No private environment credentials are needed on the runner. Responses of 200
mean received; 202 means received with key validation pending. Neither promises
indexing. Notifications are shared with participating search engines.

Requests have timeouts and bounded retries for network errors, 5xx responses,
and short numeric 429 Retry-After delays. Long/unspecified rate limits and permanent
errors stop the notification step visibly. A notification failure does not roll
back a healthy application deployment.

## Manual checks and recovery

From an app environment (uses configured `SITE_URL`):

```sh
uv run python manage.py submit_indexnow --dry-run
uv run python manage.py submit_indexnow
```

Or from a checkout, with only Python 3 installed and no Django configuration:

```sh
python3 apps/pages/indexnow.py --site-url https://tastefulkit.com --dry-run
python3 apps/pages/indexnow.py --site-url https://tastefulkit.com
```

For a failed notification, download the **original deployment's**
`indexnow-before-<sha>` Actions artifact, then retry with that snapshot:

```sh
python3 apps/pages/indexnow.py --site-url https://tastefulkit.com --previous indexnow-before.json
```

Retain the original artifact when retrying: rerunning the whole deployment takes
a fresh snapshot of the already-updated site and may omit deleted pages. The
manual retry does not redeploy the application. A snapshot contains only public
URLs; it is validated against the canonical HTTPS origin before submission.
Sitemap indexes are rejected explicitly; extend the reader before changing the
site to a multi-file sitemap. Batches are capped at the protocol's 10,000 URLs.
