---
title: Design Library API
description: Search published design references, paginate results, and fetch fresh screenshot links using the TastefulKit API.
---

# Search the design library

API and MCP access, including available DESIGN.md guides, is free. Create an account
and generate an API key in [Account settings](/settings). No subscription is required.


Use your [personal API key](/docs/api-reference/introduction/) to read published, ready-to-view designs.

```bash
curl 'https://tastefulkit.com/api/v1/designs?q=warm%20minimal&kind=landing_page' \
  -H "Authorization: Bearer $TASTEFULKIT_API_KEY"
```

## Filter and paginate

All query parameters are optional:

| Parameter | Use |
| --- | --- |
| `q` | A text description, such as `warm minimal`. |
| `kind` | Use `landing_page`, `pricing_page`, `hero`, `cta`, `auth_form`, `blog`, `navigation`, `footer`, `dashboard`, or `other`. |
| `tag` | A style tag from the library. |
| `industry` | An industry from the library. |
| `site` | A site UUID from a design response; returns references from that site. |
| `page` | A page number, starting at `1`. |

Filters combine, just as they do in Explore. URL-encode spaces and other special characters in parameter values.

The response contains `items`, `page`, `pages`, `total`, and `search_mode`. Each page contains up to 24 designs. Use `pages` to decide whether to request another page. An empty search returns an empty `items` list.

Each design includes its ID, title, description, source URL, tags, and screenshot links. Keep the ID if you want to fetch the same example again.

## Fetch one design

Replace `DESIGN_ID` with an ID returned by search:

```bash
curl 'https://tastefulkit.com/api/v1/designs/DESIGN_ID' \
  -H "Authorization: Bearer $TASTEFULKIT_API_KEY"
```

The detail response includes `design_markdown`: the complete DESIGN.md text when available, or `null` when no guide is available. `design_markdown_locked` remains `false` for compatibility. List/search results omit guide fields.

Screenshot links expire after 15 minutes. Fetch the design again for fresh links instead of storing an image URL as a permanent reference.

## Handle errors

- **401:** Check your API key and request header.
- **404:** The design does not exist or is not available to your account.
- **422:** Check parameter types, including the page number or design ID.

Ordinary accounts only see published designs with ready screenshots. This read API does not manage your Saved list; use the website to save or remove references. The [interactive schema](/api/docs) provides the complete request details.

## Free design guides

Design details include available DESIGN.md text for every active account.
A reference without a guide returns `design_markdown: null`.
`design_markdown_locked` remains `false` for compatibility. List and search
responses do not contain guide text; fetch a design by ID to retrieve its guide.

## Group references from the same site

Each response includes `site`: either `null`, or an object with `id`, `name`, and
`url`. Detail responses also include up to six published, ready `related_designs`
from that site. Use the `site` filter to paginate the complete group. REST and MCP
list/search tools accept this filter.
