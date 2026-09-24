# TastefulKit organic search strategy

Updated September 24, 2026. This is a content plan, not a forecast or a claim that
these pages already rank. Source observations and keyword estimates remain in the
existing private Rowset SEO datasets and OpenSEO project referenced by
`.seo/config.json`.

## Positioning

Help founders, developers and designers choose a landing-page direction and turn
real references into a buildable brief. TastefulKit is a reference library with
pairwise voting, global and personal rankings, design guides and a read-only MCP
connection. It is not a landing-page builder, a source-code marketplace, a
conversion-testing service or a licence to copy another site's assets.

Public articles should give a useful result without requiring payment. Point
readers toward the free Arena and global rankings when they need to compare;
explain the free account requirement before directing them to full references,
personal rankings or MCP. DESIGN.md guides require a paid membership; other reference
metadata and screenshots stay free. MCP also requires a personal API key. Never describe preference scores as
conversion data.

## One intent, one owner

| Search intent | Primary owner | Supporting phrases | Reader's next step |
|---|---|---|---|
| Find a library of real landing pages | `/` | landing page inspiration; landing page examples; website design inspiration | Try Arena or inspect global rankings |
| Turn loose ideas into a coherent page brief | `/blog/landing-page-design-ideas/` | landing page design ideas; choosing landing page references | Write a brief and compare references |
| Choose an expressive layout without sacrificing clarity | `/blog/creative-landing-page-design/` | creative landing page design; creative landing page ideas | Select one creative constraint |
| Evaluate and adapt mobile layouts | `/blog/mobile-landing-page-design/` | mobile landing page design; mobile landing page inspiration | Review a narrow-screen reference and live interaction |
| Give a coding agent a useful visual specification | `/blog/design-references-ai-coding-agents/` | design references for AI coding agents; landing page design brief for AI | Read MCP docs and create a free account |
| Connect an MCP client | `/docs/api-reference/mcp/` | TastefulKit MCP; TastefulKit API key | Complete authenticated setup |

The blog index owns navigation, not another copy of the homepage's gallery
intent. Mobile-design and coding-agent phrases are editorial hypotheses, not
keywords with a verified exact-match volume. Do not relabel the cached phrase
“best mobile landing pages” as their volume. The mobile article is a review
method, not an unsupported “best websites” ranking.

## Why these four posts

Broad inspiration searches compete with established visual galleries. A generic
“best landing pages” list would add little without a carefully maintained set of
examples. Start with narrower decisions close to the product instead: choosing,
composing, adapting to mobile, and handing off. Each article contributes a usable
original framework or worksheet; none needs invented customer results.

The initial keyword research suggests demand around landing-page examples,
inspiration, creative design and design ideas. Search Console has not yet
provided a usable page-level performance baseline for the sampled window. Treat
this as early discovery: absence of rows is not evidence that the audience or
market is absent, and it does not justify pruning new pages.

The coding-agent article is the differentiation bet. Keep it narrow: reference
selection, explicit constraints, DESIGN.md review, screenshot limitations and
visual acceptance criteria. Do not turn it into an unverified roundup of clients
or repeat connection instructions already maintained in the docs.

## Launch foundation

- Keep content in `apps/pages/content/blog/`, reviewed and shipped through PRs.
- Render full article text on the server, publicly accessible with a self-canonical
  URL, unique metadata, visible dates and BlogPosting/BreadcrumbList schema.
- Use real publication/update dates in the sitemap; hide drafts and future posts.
- Link the hub from public navigation, and give each article links from the hub,
  the homepage and related articles. Use meaningful in-body links to docs and
  appropriate product entry points.
- Preserve authentication and administrator-only ingestion boundaries. Login redirects
  are not
  broken links to “fix” by making account-only content public.
- Refresh stale internal product guidance when shipped features change. The
  older “voting is roadmap-only” guidance is no longer correct.

## Next 90 days

### First two weeks: establish discoverability

Verify deployment, sitemap, canonical URLs, mobile layout and public reachability.
Inspect homepage/blog/article URLs in Search Console after Google has had time to
crawl. If articles remain unknown, investigate discovery and rendering before
publishing another batch. Submission is not proof of indexing.

### Weeks three through six: improve the first cohort

Keep these four URLs as a fixed launch cohort. Review query/page impressions,
clicks and position together. Consider title/snippet work only when there are
enough impressions to interpret it. Review indexing and internal links before
calling a low-traffic article unsuccessful. Preserve a 21-day routine rewrite
cooldown; correctness and technical defects can be fixed immediately.

The manual OpenSEO tracker remains manual. Use the existing saved terms and dated
research before buying more keyword data. Do not enable paid recurring checks or
create a daily publishing quota as part of this launch.

### Weeks six through twelve: expand where evidence supports it

Prioritize substantive, public, curated pages for a style or use case only when
there is both demand and enough real examples. Avoid hundreds of indexable
filter combinations. A comparison with another gallery needs current, sourced
facts and honest cases where that alternative wins; do not publish thin
alternative pages just to collect competitor searches.

A useful future differentiator is an editorial analysis of public design choices
with annotated references. Publish voting statistics only after a defensible
sample, reproducible method and privacy review; never infer conversion lift from
Elo or claim the sample represents all designers.

## Measurement and acquisition

Primary outcome: qualified visits that lead to free-account activation and reference
use, not article count. Report three layers separately:

1. Discoverability: index status and non-brand impressions for the fixed cohort.
2. Engagement: article-to-Arena, rankings, docs and signup navigation where
   privacy-safe event collection has been verified.
3. Activation: successful signups and meaningful reference use attributable to
   content, once the acquisition
   path and success-event semantics have been validated.

Current conversion attribution and field Core Web Vitals are not established by
this work. Do not substitute raw pageviews, a single lab run or a null report for
those measurements. Never add API keys, private design identifiers or user data
to tracking properties.

Earn references with useful public worksheets and examples. Outreach and social
publishing require separate authorization; this plan sends no messages and buys
no links. Preserve the live product's speed by using existing styling and small
server-rendered pages rather than a client-side blog framework.
