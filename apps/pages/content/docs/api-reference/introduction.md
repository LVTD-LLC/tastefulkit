---
title: API basics
description: Connect a script or agent to TastefulKit with a personal API key and read existing catalogue data.
---

# Read TastefulKit from a script or agent

The API lets you search the design library, fetch a design, and check which account a key belongs to. You can read this documentation without signing in; API requests require a personal API key.

## Get a key

Sign in and open [Settings](/settings). Under **API access**, choose **Generate key** and store the key securely as `TASTEFULKIT_API_KEY` in your local environment. If a key already exists and you no longer have it, **Rotate key** creates a replacement and invalidates the previous one.

## Send the key in a header

The API base URL is `https://tastefulkit.com/api`. Send the key using `Authorization: Bearer`, not a URL parameter.

```bash
curl 'https://tastefulkit.com/api/user' \
  -H "Authorization: Bearer $TASTEFULKIT_API_KEY"
```

This request checks your key and returns basic details for its account. See the [User API](/docs/api-reference/user/) for the response shape.

## Search and fetch designs

Follow the [Design Library API guide](/docs/api-reference/design-library/) for filters, pagination, and screenshot links. The [interactive API schema](/api/docs) lists the available request fields and endpoints. Complete prepared catalogue submissions are restricted to administrators; a regular account key grants no write access. The app does not capture or enrich submitted examples.

## Resolve authentication errors

HTTP **401** means the key is missing, invalid, inactive, or not authorized for the operation. Check that your environment variable is set, send the header, and replace an old key if you rotated it. Signing into the website alone does not authenticate a script's request.

Do not put keys in browser-side JavaScript, shared screenshots, public repositories, or logs.
