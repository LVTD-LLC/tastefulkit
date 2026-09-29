# UI library ingestion (operators only)

UI libraries are distinct catalogue records (`kind: ui_library`), with a one-to-one
`UILibrary` metadata record. Design owns the screenshot, moderation, vector, saves
and ballots, so visibility and vote security have one implementation. Do not
create standalone metadata or reuse a landing-page ID: a library and a reference
from its website are different items. They may share optional `site` metadata.

## Submit a prepared bundle

`POST /api/v1/ui-libraries` uses the same active-superuser API key authentication,
multipart assets and synchronous storage/indexing as
[design ingestion](design-ingestion.md). The write route is omitted from public
OpenAPI and user docs. Staff and regular user keys cannot submit.

Send JSON `payload`, `screenshot`, `thumbnail`, and UTF-8 `design_md` files. Supply
`captured_at`, `viewport_width`, the prepared 768-dimensional `embedding` and
`embedding_model` exactly as for designs. No capture, scraping or inference runs
on the server. The screenshot should show the library's landing page; thumbnails
are required for fast directory and arena previews. DESIGN.md describes that
visual reference, not a license to use the library's source code.

Payload additions/example (replace the illustrative fields and prepare the real
assets/vector before posting):

```json
{
  "name": "Example UI",
  "source_url": "https://example.com/ui",
  "description": "Reusable UI components with framework-specific implementation examples.",
  "library": {
    "website_url": "https://example.com/ui",
    "github_url": "https://github.com/example/ui",
    "frameworks": ["React", "Tailwind CSS"],
    "notes": "Explain compatibility, accessibility, installation approach, licensing and useful tradeoffs. Separate verified facts from editorial observations.",
    "pricing": [
      {"name": "Community", "billing": "free"},
      {"name": "Personal", "billing": "one_time", "amount": "49.00", "currency": "USD"},
      {"name": "Team", "billing": "recurring", "amount": "15.00", "currency": "USD", "interval": "month", "notes": "Per seat"}
    ],
    "pricing_url": "https://example.com/pricing",
    "pricing_checked_at": "2026-09-29"
  }
}
```

- `name` (or `title`), `source_url`, `description` and `library` are required along
  with the existing prepared bundle fields. `kind` defaults to `ui_library`;
  selectors are not supported. Source can be the website or repository for
  repo-only libraries. Keep the same canonical source for later updates.
- Collect both website and GitHub repository when available. Optional metadata
  links can be blank. GitHub must identify `github.com/owner/repository`.
- Frameworks are explicit labels; use `Framework agnostic` only when verified.
- Pricing is a list, allowing one-time and recurring offers together. Recurring
  plans require `month` or `year`; record per-seat, taxes, billing commitments and
  limitations in plan notes. `contact` means contact for pricing. An empty list
  means unknown/unconfirmed, **not free**. Numeric amounts are decimal strings;
  use uppercase three-letter currency codes. Never invent a current price.
- `201` creates/publishes; `200` with no replacement is unchanged. Identity is
  canonical source URL + library kind, independent of screenshot width. Use
  `replace_existing: true` with a complete bundle to update; it preserves the ID,
  votes, saves, submitter and moderation visibility. Metadata replacement is
  atomic with the design/database write; failed storage/indexing rolls back.
- Public directory and full editorial pages: `/ui-libraries/` and
  `/ui-libraries/{id}/`. Only published, ready libraries are visible/indexable.
- Read APIs: `GET /api/v1/ui-libraries?q=react&page=1` and
  `GET /api/v1/ui-libraries/{id}` (active-account API key). Existing design
  REST/MCP search also accepts `kind=ui_library` and returns `library` metadata.
- Arena/rankings: `?kind=ui_library` compares libraries only, using screenshots
  and the existing viewport-family rules. Default arena/rankings/homepage stay
  landing-page focused. At least two compatible libraries are needed to vote.

## Pilot checklist

Research the requested candidates: shadcn/ui, Tailwind Plus, interior.dev,
Beautiful UI and Cuelume. They are candidates, not seeded or verified records.
Capture and inspect real screenshots; verify links, descriptions, framework
claims, prices and licenses against their primary sources. Submit two compatible
libraries, read back metadata and image hashes, inspect public directory/detail,
and confirm a library-only arena pair before expanding recurring collection.
Do not cast production votes merely to test ingestion.
