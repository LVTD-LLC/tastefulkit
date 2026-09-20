# Changelog

## 2026-09-20

- Add a custom homepage share image and automatic branded previews for docs, rankings, membership, legal pages, and published landing-page references. Shared design links now show public title-and-thumbnail teasers while full details, design guides, and saves remain members-only.

- Add a branded Arena link preview with real side-by-side design references and complete Open Graph/Twitter image metadata.

- Make all documentation public for logged-out and unpaid visitors, including API/MCP setup guides; restore API-reference sitemap entries and indexing while keeping paid product features protected.

- Show lightweight Arena previews before decoding full screenshots in the background; retain screenshot voting and full-page scrolling. Remove the Arena reassurance, skip button, account-ranking footnote, and homepage how-it-works/final CTA sections.

- Restore six homepage landing-page previews in global-ranking order, with a link to the full public ranking; keep catalog and design-guide access membership-only.

- Replace navbar theme text with a circular sun/moon icon toggle to the right of Get started; retain accessible labels, keyboard controls, and saved theme preferences.

## 2026-09-19
- Make global rankings public for guests and unpaid accounts; keep personal rankings, taste reset, and design-library/API access membership-only.

- Add one $10 USD/month membership with Stripe-hosted checkout, self-service billing, signed/idempotent subscription webhooks and server-side paid access for browsing, rankings, design guides and API/MCP. Keep Arena free; prevent orphaned billing on account deletion. Update setup and product documentation to the landing-page-only offer.

- Focus browsing and comparisons on landing pages, simplify homepage copy and actions, remove decorative labels and element filters, and let Arena screenshots cast accessible keyboard/touch votes without routine success banners.

- Opened the voting arena and global rankings to visitors without an account. Guest votes contribute to global Elo with session-bound pair tokens, duplicate protection, CSRF checks, and per-session rate limits.
- Kept personalized rankings and taste resets account-only, with an optional signup link for guests to build a personal ranking from future votes.

## 2026-09-18

- Added a signed-in-only design voting arena with comparable pairs, skips, duplicate protection, and per-account rate limiting.
- Added global Elo rankings with comparison counts/category filters and private personalized rankings learned from choices and saves, including a cold-start fallback and taste reset.
- Added atomic, replayable vote history and responsive, keyboard-accessible arena/ranking pages.

## 2026-09-16

- Accept complete, agent-prepared examples through the admin-only multipart POST: supplied screenshots, thumbnails, DESIGN.md, capture timestamp and compatible embedding are validated, stored and indexed without application-side generation.
- Add protected DESIGN.md viewing, copying, downloads and REST/MCP detail retrieval. Preserve existing references and support explicit complete-bundle replacement for external backfills.
- Retire capture/retry entry points and MCP writes; old queued jobs are inert and vector backfill no longer invokes inference. Search-time query embeddings remain supported.

## 2026-09-15

- Remove the separate IndexNow operations runbook; keep the manual notification recovery hint next to the automated deployment step.

- Enable IndexNow verification and public-sitemap submission after verified deployments, including removed URLs from a retained pre-deploy snapshot, bounded retries, and a manual recovery command.

## 2026-09-12

- Clarify the homepage search and social preview metadata around the shipped design-reference library, search, saved designs, API, and MCP; establish private Rowset-backed SEO run tracking.

- Rewrite the README for product users, move application engineering and operations details into AGENTS.md, and add contributor guidance requiring a current-head ReviewGate 5/5 before merge.

- Enable ReviewGate pull request reviews from its `main` branch, with general/adversarial checks, structured results, and maintainer-requested rereviews using the existing OpenRouter secret.

- Add authenticated hosted MCP at `/mcp/` in a dedicated Django app, sharing REST search, metadata, screenshot references, account info, and administrator submission/retry behavior. Include filter discovery, setup docs, revocation/permission/parity tests, and multi-worker ASGI serving.

- Enable configured PostHog analytics by default for visitors and signed-in users; remove the opt-in banner and account-event consent gates, migrate legacy opt-out state, and update analytics disclosures while preserving URL/property sanitization.

- Fix docs link hover so only the hovered link is underlined; restyle docs navigation in the warm, compact product language with a native mobile menu and accessible current-page state.

- Make all website documentation public and indexable, without changing library, account, or API authorization.
- Replace starter/deployment docs with guides to shipped browsing, search/filtering, saved-design, account, and read-only API features; keep operator references outside website routes.

- Adopt the approved reference-stack logo across public and app headers/footers, with theme-aware branding, matching browser/touch icons, and a first-party social preview.

- Fix Qdrant SDK client lifecycle handling discovered during live rollout; verify actual SDK cleanup in regression coverage.

- Move live embedding storage and similarity ranking to an isolated internal Qdrant service.
- Preserve authoritative catalogue filters, saved-design ownership, and visibility checks; retain keyword fallback.
- Add idempotent legacy-vector backfill, explicit regeneration, bounded indexing retries, and Qdrant health checks.
- Document persistent CapRover provisioning, recovery, and rollback; retain legacy vectors without querying them.

## 0.1.1 — 2026-09-12

- Pace screenshot captures and schedule bounded provider retries.
- Capture after DOM readiness and a short render settle, avoiding endless network-idle waits.
- Keep the interface functional when analytics is not configured.

## 0.1.0 — 2026-09-12

- Generate TastefulKit from the official djass template.
- Add design catalogue, private screenshot storage, background capture and embeddings.
- Add authenticated search, filters, saved designs, and admin-only ingestion/retry API.
- Remove automatic first-signup administrator promotion.
- Configure public GitHub repository and split CapRover web/worker deployment.
