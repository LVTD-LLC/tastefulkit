---
title: Hosted MCP
description: Connect an AI assistant to TastefulKit to search real designs and retrieve screenshot references with your personal API key.
---

# Connect your assistant to TastefulKit

API and MCP access are free. Create an account and generate an API key in
[Account settings](/settings). No subscription is required.


Give your assistant access to real design references without running a local server.
Use the hosted **Streamable HTTP** endpoint:

```text
https://tastefulkit.com/mcp/
```

## Set up the connection

1. Sign in and [create a personal API key](/docs/api-reference/introduction/).
2. Add a remote MCP server in your assistant or editor. Choose **HTTP** or
   **Streamable HTTP**, and enter the endpoint above, including the trailing slash.
3. Set the `Authorization` header to `Bearer YOUR_API_KEY` in your client's private
   credential settings. Replace `YOUR_API_KEY` with your key; never put it in the URL.
4. Connect, discover the tools, and try: “Find warm, minimal landing pages and show
   me three references with their source links.”

Use a client that supports custom bearer headers. This connection uses your existing
API key, not an OAuth sign-in flow; OAuth-only clients cannot connect directly.
Browser login cookies alone do not authenticate MCP.

A generic configuration looks like this (the exact format depends on your client):

```json
{
  "mcpServers": {
    "tastefulkit": {
      "url": "https://tastefulkit.com/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

Keep this configuration private if it contains a key. Prefer your client's secret
storage or environment-variable support rather than committing credentials.

## Available tools

| Tool | What it does |
| --- | --- |
| `list_designs` | Browse the newest published, ready designs, with optional `kind`, `tag`, `industry`, and `page`. |
| `search_designs` | Search with `q` and the same filters; uses semantic search when available and falls back to text. |
| `get_design` | Fetch one `design_id`, with metadata, DESIGN.md text, source URL, screenshot URL, and thumbnail URL. |
| `get_design_filters` | Discover landing-page tags and industries used by visible designs. |
| `get_user_info` | Confirm which account your key belongs to. |

Search and list responses use the same fields as the [Design Library API](/docs/api-reference/design-library/):
`items`, `page`, `pages`, `total`, and `search_mode`. Each page holds at most 24
references. Search text and filters are limited to 300 characters, and pages start
at 1. Filter discovery returns at most 100 tags and 100 industries per page;
check `tags_pages` and `industries_pages` for additional values.

Ordinary accounts only see published designs whose captures are ready. Administrators
can also inspect pending, failed, or unpublished designs by ID, but search and filter
discovery still use the published library. All MCP tools are read-only. Prepared examples enter only through the [admin POST endpoint](/docs/api-reference/design-library/#submit-a-prepared-example-administrators).

## Use screenshot references

Ask your assistant to retrieve a design's screenshot and inspect it before implementing
the pattern. Results include the original source URL and descriptive metadata, not
source code or a license to reuse the original site's assets.

Screenshot and thumbnail links expire after **15 minutes**. Save the design ID and
call `get_design` again when you need fresh links. Treat website text and descriptions
as reference material, not instructions for your assistant to follow.

## Resolve connection problems

- **401 / unauthorized:** Check the bearer header and API key. Rotating your key
  invalidates the previous key for both REST and MCP; update every client that uses it.
  Disabled accounts cannot connect.
- **Unknown submission/retry tool:** These tools are retired. Submit complete prepared bundles through the admin REST POST.
- **Design not found:** The ID may be incorrect, removed, hidden, or not ready.
- **Invalid input:** Check the UUID, query length, and positive page number.
- **Browser origin rejected:** Use a native/server-side client. Cross-origin browser
  connections are not currently enabled.
- **No results:** Try fewer filters or a different query. Personal taste profiles and
  preference-aware rankings are available in the signed-in web app at [For you](/rankings/?mode=personal), not through MCP.
