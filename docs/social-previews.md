# Social previews

| Surface | Image | Public content |
| --- | --- | --- |
| Homepage | Custom 2400×1260 PNG | Marketing page and existing top-six previews |
| Arena | Approved 2400×1260 matchup PNG | Existing public voting page |
| Global rankings, membership, legal, technology | Generated 1200×630 PNG | Existing page content |
| Docs | Generated title/description card for each navigable article | Repository-tracked documentation |
| Published ready landing-page references | Generated title + stored thumbnail | Title-and-thumbnail teaser for guests/unpaid users; full page for paid members |
| Sign-in/signup | Homepage artwork with route-specific metadata | No account data or query parameters |
| Personal rankings, saved library, settings, admin, password and verification flows | No personalized social card | Existing access restrictions |

`apps/pages/social.py` owns the finite public-page metadata registry and doc-card
routes. `components/page_metadata.html` renders one consistent set of canonical,
Open Graph and Twitter tags. Existing indexing directives are preserved.

The homepage and Arena artwork live under `frontend/src/brand/`; their PNGs ship
in static assets. The other images are served from `/social/pages/<key>.png`,
`/social/docs/<category>/<page>.png`, and `/designs/<uuid>/social.png`.
All image URLs are first-party and stable; metadata never embeds signed R2 URLs.
The metadata follows the [Open Graph protocol](https://ogp.me/), including image
size, MIME type, and descriptive alt text.

The renderer uses Pillow and a bundled Inter font, with its license in
`apps/pages/assets/Inter-OFL.txt`. It does not run a browser, fetch a source
website, or call an external image service. The renderer is separate from
ingestion; original uploaded screenshots and thumbnails remain unchanged.

Page/document cards cache by content for an hour and allow five minutes of HTTP
caching. Design cards check publication, ready status, and landing-page kind
before consulting their one-hour cache. Their key includes the current title,
thumbnail filename, and modification time. Design HTTP responses use `no-store`;
hiding/deleting a reference prevents subsequent origin requests from serving a
cached image. Already copied images in social platforms' own caches cannot be
revoked by the app. Missing, unreadable, or oversized thumbnails produce a branded
text fallback, cached for only one minute. No full screenshot or DESIGN.md is read
by the image generator.

For copy changes, update the registry or doc frontmatter. For a design update,
submit a complete replacement bundle as usual. Bump the cache version prefixes
in `apps/pages/social.py` and `apps/catalogue/social.py` after renderer changes.
No backfill, migration, or background worker is needed.

Verify against a configured test database:

```sh
make pytest-check -- apps/pages/test_metadata.py apps/pages/test_social.py apps/catalogue/tests/test_social.py -q
make frontend-check
```

Inspect the generated PNGs at full and feed size and check
public teasers at mobile/desktop widths in both themes.
