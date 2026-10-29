# Blog authoring

The public blog is managed entirely in Git. Add a Markdown file to
`apps/pages/content/blog/` and ship it through the normal PR and review process.
No admin entry, migration, CMS account, or membership is needed to read a post.

## File and metadata

Use a stable lowercase, hyphenated filename such as `landing-page-references.md`.
It becomes `/blog/landing-page-references/`; do not rename a published file
without a redirect plan. Start with YAML frontmatter:

```yaml
---
title: "How to choose landing page references"
description: "A practical workflow for choosing references that fit your product."
author: "TastefulKit"
date: 2026-09-20
updated: 2026-09-20
draft: false
---
```

`title`, `description`, `author`, and `date` are required. `author` names the
publishing organization/team, matching the structured-data organization byline.
Dates must be real `YYYY-MM-DD` dates. `updated` is optional and defaults to
`date`; it cannot precede publication. Use the actual first-publication date,
and change `updated` only for a substantive edit. Do not refresh dates merely
because a build ran. The published and modified dates appear in metadata,
structured data, and the sitemap; a changed date also appears in the byline.

`draft` is an optional YAML boolean, defaulting to `false`. Drafts, future-dated
posts, future updates, invalid metadata, and empty posts are excluded everywhere:
index, related links, sitemap, and direct URLs (404). Dates use the configured
Django timezone. Future posts become eligible on the given date without a rebuild.
Invalid content emits a structured warning, but does not break other posts.

## Body and links

Library roundups may include a `roundup_items` list in frontmatter. Each item
has a `name` and a local `/ui-libraries/<uuid>/` `path` that also appears in the
body. List only the main recommendations, in their visible order. The renderer
adds an unordered `ItemList` alongside the existing article and breadcrumb
schema; positions describe presentation order, not ratings. Do not add reviews,
scores or claims of testing through this metadata.

Each listed library's public detail page links back to its published comparison
guides. This uses the exact `roundup_items` path, not a framework or name guess.
Keep that list aligned with the visible recommendations. Draft, future-dated and
invalid guides are excluded; libraries absent from the lists show no comparison
section.

In comparison tables, link each recommended library name to its matching public
reference from `roundup_items`. Readers should be able to inspect a candidate
directly from the shortlist; keep the descriptive comparison cells unchanged.

The template supplies the H1. Use `##` and `###` headings in the body; these build
a server-rendered, keyboard-accessible table of contents. Fenced code and tables
are supported. Write concise paragraphs and descriptive link labels. Include
links to relevant sibling posts and product/docs pages, accurately distinguishing
public browsing, screenshots and available DESIGN.md guides from account-only
saves/personal rankings and API-key access. Do not imply a paid tier or a
free-forever promise.

Markdown is trusted, code-reviewed repository content, like the existing docs;
raw HTML is not a user-upload surface. Do not add scripts or unreviewed embeds.
Frontmatter is escaped in HTML and JSON-LD. Blog rendering requires no JavaScript.

An optional `related` frontmatter list selects up to three other article slugs
in editorial order for “Keep reading”. Use existing, relevant guides; do not
include the current slug or duplicates. Only currently published targets appear:
drafts, future posts and missing targets are omitted without substituting
unrelated articles. Without a nonempty list, the section uses the latest other
published articles. Substantive changes to these recommendations should update
`updated`. These links use the existing privacy-safe marketing CTA event with
`related_guide` / `related_guides` labels; navigation is not activation.

The index is newest-first and links every published post. Each article links to
its eligible related guides and back to the index. The global navigation
and footer link to the blog on public pages.

## Verify

Run `make pytest-check -- apps/pages/test_blog.py -q`, then the relevant checks
in [quality.md](quality.md). The content contract test loads every real file so
malformed metadata fails CI instead of silently disappearing. Preview the index
and article on desktop/mobile in both themes. Confirm canonical URLs, heading
anchors, internal links, real publication/updated dates, and product claims.
