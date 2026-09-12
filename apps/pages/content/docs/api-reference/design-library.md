---
title: Design Library API
description: Search published design references, paginate results, and fetch fresh screenshot links using the TastefulKit API.
---

# Search the design library

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
| `kind` | An element type: `landing_page`, `pricing_page`, `hero`, `blog`, `navigation`, `footer`, `dashboard`, or `other`. |
| `tag` | A style tag from the library. |
| `industry` | An industry from the library. |
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

Screenshot links expire after 15 minutes. Fetch the design again for fresh links instead of storing an image URL as a permanent reference.

## Handle errors

- **401:** Check your API key and request header.
- **404:** The design does not exist or is not available to your account.
- **422:** Check parameter types, including the page number or design ID.

Ordinary accounts only see published designs with ready screenshots. This read API does not manage your Saved list; use the website to save or remove references. The [interactive schema](/api/docs) provides the complete request details.
