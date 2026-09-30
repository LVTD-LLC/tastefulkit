# AI skill ingestion (maintainers only)

Collect design-relevant agent skills: interface composition, typography, accessibility,
design review, or frontend workflows. Research the upstream source; describe concrete
uses and limitations. Do not submit generic unrelated skills or infer compatibility/licensing.
This directory is independent of screenshot references and UI libraries and has no voting.

## Endpoint and authentication

`POST /api/v1/ai-skills`, `Content-Type: application/json`, using the existing
collector API key in `Authorization: Bearer $TASTEFULKIT_API_KEY` or `X-API-Key`.
Only active superusers may write; regular accounts/staff and inactive accounts cannot.
The endpoint is intentionally absent from public OpenAPI and product docs.
Never put credentials in payloads, URLs, Git, or logs.

No screenshot, thumbnail, DESIGN.md, embedding, or uploaded executable is required.
The app stores supplied text and URLs only: no fetching, installation, or execution.

```json
{
  "name": "Example interface review",
  "source_url": "https://github.com/example/skills/blob/main/interface-review/SKILL.md",
  "website_url": "https://example.com/skills/interface-review",
  "repository_url": "https://github.com/example/skills",
  "description": "Reviews interface hierarchy, spacing, and accessibility before shipping.",
  "notes": "Use after implementing a screen. Explain the expected input, output, and limitations here.",
  "installation": "Follow the upstream installation instructions for this specific skill.",
  "compatible_agents": ["Codex", "Claude Code"],
  "tags": ["design-review", "accessibility"],
  "license": "MIT",
  "checked_at": "2026-09-30",
  "replace_existing": false
}
```

Example only; do not publish it. Required: `name` (2–160 chars), `source_url`
(HTTP/S, at most 2048 chars), `description` (10–5000 chars). Optional URLs at most
2048 chars, `notes`/`installation` at most 10000, `license` at most 160.
Agent/tag lists allow at most 20 nonempty labels of at most 60 chars each.
Omit unconfirmed optional information; use an ISO date for `checked_at` when verified.
Unknown fields are rejected. Submitted HTML is displayed as escaped text.

Use the specific skill's canonical source URL, not a shared repository root: multiple
skills may live in one repository. URL scheme/host case and fragments are normalized;
paths and query strings are retained. Prefer stable URLs without tracking parameters.

- **201**: created and published.
- **200**: same normalized source URL already exists; unchanged unless
  `replace_existing: true`. Replacement is a full metadata replacement, retaining ID,
  submitter, original creation date, and moderation visibility. Omitted optional fields clear.
- **401**: missing/invalid key, inactive account, or no superuser permission.
- **422**: invalid payload. Correct it before retrying.

Concurrent retries use a unique source URL constraint; replacements lock the existing
row. No production entries are seeded by migrations. Django admin can hide/unhide entries.

## Verify a submission

1. Confirm returned metadata and stable `id`/`url`; repeat identical submissions return 200.
2. Check public `/ai-skills/` search and returned detail URL; verify links, readable setup,
   use cases, compatibility, and license against the source.
3. Confirm published detail URLs appear in `/sitemap.xml`. Hidden entries must return 404.
4. Authenticated `GET /api/v1/ai-skills?q=...&page=1` and
   `GET /api/v1/ai-skills/{id}` expose published entries only, with 24 per page.

Existing hosted MCP design tools do not include AI skills. Do not send skills to
`/api/v1/designs` or `/api/v1/ui-libraries`. Scheduling/research remains the external
collector's job; this feature does not change its cron.
