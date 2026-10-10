# Changelog

## 2026-10-10

- Add a pricing-page reference-selection guide with three sourced examples, a worked borrow/adapt/reject brief, and checks for billing clarity and mobile presentation.

## 2026-10-09

- Connect AI-skill details to public design references, the coding-agent briefing guide and UI libraries. Explain how skills, visual references and implementation components work together without implying automatic installation or AI-skill search through the design MCP tools.

## 2026-10-08

- Add weekly double-opt-in newsletter signup on the homepage and design/UI-library details, with CSRF protection, shared rate limits, validation, and recoverable provider errors. Listmonk manages confirmation/unsubscribe; no account or preconfirmed subscription is created.

- Add Sentry error reporting, sampled traces and trace-lifecycle Python profiles,
  structured logs, request/job metrics, browser monitoring and masked anonymous
  replay. Exclude private replay surfaces and scrub request content. Document
  sampling, verification and rollback; update the privacy notice.

## 2026-10-05

- Negotiate Markdown automatically from rendered public HTML pages with shared
  middleware, preserving their content, links, permissions and HTML defaults.
  Exclude account/admin/form and protocol routes, preserve cache behavior, and
  provide explicit view/element opt-outs without separate Markdown templates.

- Return a Markdown explanation and documentation/sitemap links for missing pages
  when clients prefer `text/markdown`, preserving HTTP 404 and the HTML browser
  response with cache-safe `Vary: Accept` content negotiation.

## 2026-10-03

- Add a shared navbar counter for PostHog production pageviews over the last 24 hours, refreshed in the background every five minutes with mobile/dark-mode support and stale-data hiding.

- Prioritize the first UI-library directory preview so its visible image can
  load promptly; keep subsequent previews lazy-loaded and preserve image dimensions.

## 2026-10-01

- Correct pricing, onboarding docs and three reference guides to explain public
  Explore, screenshots and DESIGN.md access. Preserve account requirements for
  saves, personal rankings and API/MCP; point key setup to How to Use. Update
  article modification dates and SEO claim checks to match the shipped policy.

## 2026-09-30

- Keep the Has motion selector inside the public Explore search form for both guests and signed-in users.

- Add optional validated silent MP4 motion previews for design references, on-demand gallery playback, Motion/Screenshot detail views and a Has motion filter. REST/MCP return clip metadata and motion notes; existing static submissions and Arena remain unchanged.

- Make all Explore browsing public, including design/component details, full screenshots and DESIGN.md downloads. Preserve account-only saves/personal rankings and authenticated APIs.

- Add a public How to Use guide for Explore, Arena and AI workflows, linked third in the left navbar. Move the account-specific installation prompt from the homepage into the guide.

- Simplify the shared navbar with Arena and Explore on the left, grouped catalogue/docs/blog links, and a username menu beside the theme toggle.

- Show source-linked GitHub repository stars and skills.sh skill installs with checked dates; sort the AI skills directory and REST results by either count, with unknown values last. Add validated collector metrics and a metadata-preserving admin refresh endpoint.

- Add a public, searchable design-focused AI skills directory with source links,
  compatibility, usage and installation notes, license metadata, and admin-only
  idempotent JSON ingestion. Published entries are included in the sitemap.
- Remove UI libraries from Arena and rankings while retaining Explore, metadata,
  saved references and historical ballots. Old comparison tokens cannot cast votes.


- Align SEO claim guidance and checks with free DESIGN.md access. Correct the four
  blog articles’ modification dates to September 29, when their access copy changed,
  preserving September 20 publication dates and existing article content.

## 2026-09-29

- Automatically provision encrypted, copyable API keys for new accounts and add an idempotent existing-account backfill that preserves legacy keys. Include the owner’s key in the renamed hero installation prompt, disable it for guests with a sign-in tooltip, place it below the main CTAs, and remove the recent-guides section and placeholder helper. Explicit rotation revokes all prior keys.

- Add a homepage hero “Copy prompt” action for installing the public TastefulKit skills and MCP, with an API-key placeholder and settings link. Preserve the original copy-button label after repeated clicks.

- Share Explore, Arena, Global ranking and For you navigation across discovery pages, with content-type tabs that preserve selection; enable component comparisons/rankings and remove Explore’s duplicate Type filter.

- Fit detail previews to each image’s proportions without enlarging small assets or leaving empty square panels; retain bounded scrolling for tall captures. Show complete, uncropped catalogue thumbnails and apply the same preview behavior to UI library details.

### UI library directory
- Added public UI library directory/detail pages with screenshots, framework notes,
  website/GitHub links, multi-plan pricing and sitemap coverage.
- Added an admin-only prepared-library API with atomic metadata replacement,
  plus authenticated read endpoints and shared REST/MCP metadata.
- Added separate UI-library arena/ranking selection without changing landing-page
  rankings, homepage previews or existing vote protections.


- Remove admin submission and site-linking instructions from public docs and hide write endpoints from the public OpenAPI schema; preserve the operator contract in repository-only maintainer notes. Endpoint behavior and permissions are unchanged.

- Add square, keyboard-scrollable detail previews, optional shared sites, related references, and page/component browsing. Admin submissions support site metadata and CTA/auth-form kinds; an admin-only site-link endpoint connects existing references without replacing assets. REST/MCP expose site metadata, filtering and related designs. Existing references remain independent until explicitly linked.


### Removed

- Remove this repository's ReviewGate PR-review GitHub Actions workflow; retain application CI and deployment workflows.


## 2026-09-29

- Made all current features free, including DESIGN.md viewing, copying, downloading, REST and MCP retrieval. Account/API-key authentication and admin-only ingestion remain unchanged.
- Disabled new checkout purchases and replaced membership upsells with free-access copy across pricing, settings, documentation, and articles. Existing subscription management, webhooks and deletion cleanup remain available; existing Stripe subscriptions and sessions are not changed by this release.

## 2026-09-25

- Distinguish published blog articles and public docs in pageview and marketing
  CTA analytics using a server-supplied public content path. Keep URL templates,
  query stripping and private-route exclusions intact, clear content identity
  on navigation, and explicitly disable session recording.

## 2026-09-24

- Make DESIGN.md the paid feature: gate viewing, copying, downloads and API/MCP
  guide text behind the existing $10/month membership; restore checkout and upgrade
  prompts. Keep Explore, For You, screenshots, saves and metadata access free.

- Correct the four starter blog posts to describe free-account access after the pricing change, preserve their publication dates, and align SEO product guidance and claim checks.

- Make all current features free for accounts: Explore, For You, saved designs,
  design guides, API keys, REST and MCP no longer require a subscription.
- Replace upgrade prompts with free-account guidance and disable new web checkouts;
  retain existing billing management, webhook reconciliation and cancellation.

## 2026-09-23

- Keep public 404 pages independent of database-backed context and analytics so
  missing URLs return 404 and valid slashless URLs can redirect normally.

## 2026-09-20

- Add responsive space between the homepage thumbnail grid and footer (48px on small screens, 64px from tablet upward).
- Add a public, repository-managed blog with four practical landing-page design guides, article metadata/schema, dated sitemap entries, and links from the homepage and navigation. Document the keyword strategy and Markdown publishing workflow; exclude drafts and future posts from public routes.

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
