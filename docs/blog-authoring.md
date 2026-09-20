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

The template supplies the H1. Use `##` and `###` headings in the body; these build
a server-rendered, keyboard-accessible table of contents. Fenced code and tables
are supported. Write concise paragraphs and descriptive link labels. Include
links to relevant sibling posts and product/docs pages, accurately distinguishing
public features from paid catalogue/API/MCP access.

Markdown is trusted, code-reviewed repository content, like the existing docs;
raw HTML is not a user-upload surface. Do not add scripts or unreviewed embeds.
Frontmatter is escaped in HTML and JSON-LD. Blog rendering requires no JavaScript.
The index is newest-first and links every published post. Each article links to
up to three other recent articles and back to the index. The global navigation
and footer link to the blog on public pages.

## Verify

Run `make pytest-check -- apps/pages/test_blog.py -q`, then the relevant checks
in [quality.md](quality.md). The content contract test loads every real file so
malformed metadata fails CI instead of silently disappearing. Preview the index
and article on desktop/mobile in both themes. Confirm canonical URLs, heading
anchors, internal links, real publication/updated dates, and product claims.
