---
title: Design Library API
description: Search real design examples and submit new entries as an administrator.
---

Use your personal API key from **Account** settings. Send it in the `Authorization: Bearer` header. Never put it in a URL.

## Search designs

```bash
curl 'https://tastefulkit.com/api/v1/designs?q=warm%20minimal&kind=landing_page' \
  -H "Authorization: Bearer $TASTEFULKIT_API_KEY"
```

Optional filters: `q`, `kind`, `tag`, `industry`, and `page`. Results contain title, description, source URL, tags, and signed screenshot URLs. Each page contains up to 24 designs. Signed image links expire after 15 minutes; fetch the design again for fresh links.

## Submit an example

Only an active administrator account can submit examples. The endpoint queues a capture; it does not wait for the screenshot.

```bash
curl 'https://tastefulkit.com/api/v1/designs' \
  -H "Authorization: Bearer $TASTEFULKIT_ADMIN_API_KEY" \
  -H 'Content-Type: application/json' \
  --data '{"title":"Example","source_url":"https://example.com/","description":"A minimal landing page with generous whitespace and expressive typography.","kind":"landing_page","tags":["minimal","editorial"]}'
```

Supported kinds: `landing_page`, `pricing_page`, `hero`, `blog`, `navigation`, `footer`, `dashboard`, `other`. Optional fields: `industry`, CSS `selector`, and `viewport_width` (320–2560; default 1440).

A new submission returns HTTP 201. The same URL, kind, selector, and viewport return the existing entry with HTTP 200. Only public HTTP(S) pages are accepted.

## Check capture progress

Fetch `GET /api/v1/designs/{id}` with your admin key. `capture_status` is `pending`, `processing`, `ready`, or `failed`. Only published, ready examples are visible to regular users.

If a capture fails, inspect `capture_error`, then retry with `POST /api/v1/designs/{id}/retry`. If embedding generation fails, the screenshot remains available through text search. HTTP 401 means the key is missing, invalid, inactive, or lacks administrator access; HTTP 422 means the submitted data needs correction.

The [interactive API schema](/api/docs) lists request fields and endpoints.
