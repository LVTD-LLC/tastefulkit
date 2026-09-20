# Arena social preview

`arena-social-preview.html` is the editable, self-contained source for
`frontend/static/brand/arena-social-preview.png`. Its 1200 × 630 canvas is captured
at 2× (2400 × 1260 pixels). It uses the existing reference-stack mark, Arial,
bold italic matchup typography, ink, warm white, and terracotta. The two real
website previews face off around a large VS. in a fighting-game-inspired layout.

The embedded Raycast and Notion thumbnails are real public catalogue previews
retrieved from the TastefulKit homepage on 2026-09-20. Their original sites are
https://raycast.com/ and https://notion.com/. The composition illustrates a
comparison; it does not represent a live pair or a ranking. Embedding the images
keeps regeneration independent of expiring signed asset URLs. Refresh this
artwork if either reference should no longer appear in public marketing.

From the repository root, with Playwright Chromium installed:

```sh
npx playwright screenshot --device="Desktop Chrome HiDPI" \
  --viewport-size="1200,630" --wait-for-timeout=1000 \
  "file://$PWD/frontend/src/brand/arena-social-preview.html" \
  frontend/static/brand/arena-social-preview.png
```

Inspect both the full image and a 400px-wide preview after changes. Keep the PNG
dimensions and the metadata in `frontend/templates/catalogue/arena.html` aligned.
Only the PNG ships as a static asset; this HTML is an artwork source, not an app
template.
