# Browser-checked landing-page guides

Run the export and apply commands against the intended catalogue. Run Chromium
on a separate preparation machine with a clean browser profile and public web
access. Keep the run directory, candidate snapshot, screenshots and before/after
guides in operator storage outside the repository. A run uses local Chromium
and visual review, with no paid inference API.

1. Export a fixed candidate pool. This selects published, ready, full-page
   landing references with an archived screenshot and an existing guide, oldest
   first. Increase the pool when sites have changed since their archive.

       python manage.py reference_guides export --limit 150 > candidates.json

2. Capture candidate pages at their archived width. Supply a local Chromium
   executable or install Playwright Chromium. Repeat with the same manifest and
   output directory to resume or retry failed captures. Use one capture process
   per run directory. Each UUID has an archive crop, a live first viewport and
   computed styles with DOM paths. Errors remain in that UUID's error.txt.

       uv run scripts/reference_review/capture.py candidates.json run --limit 150 --chromium /usr/bin/chromium

3. Compare archive.jpg and live.jpg side by side for each UUID. Skip redesigns,
   challenges, unreadable pages and unrelated redirects. Inspect evidence.json
   and select visible elements whose text and position match the screenshots.
   CSS describes the sampled node at that viewport, including its computed
   font stack. Descendant text or gradients can paint differently. Record the
   layout, a component relationship and a concrete adaptation in your own words.
   Approve each selected UUID with its own notes and two or more sample indices.
   Indices start at zero in headings (h), paragraphs (p), controls (c) and
   navigation (n). Archived front matter stays as originally submitted.

       python scripts/reference_review/prepare.py candidates.json run approve "$id" "$summary" h0 p0 c1
       python scripts/reference_review/prepare.py candidates.json run build > reviewed.json

4. Dry-run the manifest first, then apply. Each row is independently locked,
   validated and compared with its export revision. An interrupted write can
   be repeated with the original manifest. A newer edit or hidden reference
   requires a fresh review. Full bundle replacement clears the review summary.
   To scale, export the next candidate pool after the checked batch is published.

       python manage.py reference_guides apply reviewed.json
       python manage.py reference_guides apply reviewed.json --write

Check the public detail HTML, DESIGN.md download and sitemap after publishing.
REST and MCP detail return the same stored guide. Literal search includes the
summary. The original embedding, screenshot, tags and capture date remain
attached to the reference.
