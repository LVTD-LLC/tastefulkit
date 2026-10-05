# Shared Markdown negotiation — review samples

Generated from the actual Django routes and middleware using disposable synthetic catalogue fixtures. These are **local previews, not production responses**. Source/asset URLs are illustrative; no real account keys or captured private data are included. Relative links resolve against the requested website URL, not this GitHub document.

HTML uses the existing templates unchanged. Markdown bodies below are exact response text, not hand-written alternate templates.

## Homepage

GET `/` with `Accept: text/markdown`

Status: 200. Content-Type: `text/markdown; charset=utf-8`. Vary: `Cookie, Accept, HX-Request, HX-History-Restore-Request`.

``````markdown
# Find your taste. Build from *it.*

Compare landing pages to rank designs around your taste. Give your coding agent the references to bring that look to your project.

[Explore catalog ↗](/explore/) [Vote on designs →](/arena/)

## Top-ranked landing pages.

[View global ranking ↗](/rankings/)

[![Editorial reference website screenshot](/media/thumbnail.png)](/designs/00000000-0000-0000-0000-000000000001/)

### [Editorial reference](/designs/00000000-0000-0000-0000-000000000001/)

Landing page · Motion
``````

## Explore

GET `/explore/` with `Accept: text/markdown`

Status: 200. Content-Type: `text/markdown; charset=utf-8`. Vary: `Cookie, Accept, HX-Request, HX-History-Restore-Request`.

``````markdown
# Find your kind of good.

[Explore](/explore/?kind=landing_page)
[Arena](/arena/?kind=landing_page)
[Global ranking](/rankings/?kind=landing_page)
[For you](/rankings/?mode=personal&kind=landing_page)

[UI libraries](/ui-libraries/)
[Landing pages](/explore/?kind=landing_page)
[AI skills](/ai-skills/)

1 design Newest first

[![Editorial reference website screenshot](/media/thumbnail.png)](/designs/00000000-0000-0000-0000-000000000001/)

### [Editorial reference](/designs/00000000-0000-0000-0000-000000000001/)

Landing page · Motion
``````

## Design detail

GET `/designs/00000000-0000-0000-0000-000000000001/` with `Accept: text/markdown`

Status: 200. Content-Type: `text/markdown; charset=utf-8`. Vary: `Cookie, Accept, HX-Request, HX-History-Restore-Request`.

``````markdown
[← Back to the library](/explore/)

Landing page

# Editorial reference

[Sign in to save](/accounts/login/?next=/designs/00000000-0000-0000-0000-000000000001/)

Warm editorial layout with clear typography.

[Visit original website ↗](https://example.com/1) Captured Oct 5, 2026 · 1440px wide

## Build with this design

Download DESIGN.md into your project and ask your coding agent to follow it alongside this reference. Review inferred values against the original before implementation.

[Download DESIGN.md ↓](/designs/00000000-0000-0000-0000-000000000001/DESIGN.md)

View DESIGN.md

````
# Design

Use generous spacing and warm colors.

```css
a { color: #b34424; }
```
````

If copying fails, download the file or select the text above.

[Video](/media/preview.mp4)



A gentle hero fade.

![Full screenshot of Editorial reference](/media/screenshot.png)

Design belongs to its original creator. Use this example for inspiration, not as a licensed template.
``````

## UI library detail

GET `/ui-libraries/00000000-0000-0000-0000-000000000002/` with `Accept: text/markdown`

Status: 200. Content-Type: `text/markdown; charset=utf-8`. Vary: `Cookie, Accept, HX-Request, HX-History-Restore-Request`.

``````markdown
[← UI libraries](/ui-libraries/)

# Example UI library

Reusable accessible controls.

React Vue

[Visit library ↗](https://example.com/ui)

## Working with this library

Accessible primitives for product interfaces.

## Pricing

### Personal

USD 49.00 · one-time

## Landing page preview

![Landing page of Example UI library](/media/screenshot.png)

Captured Oct 5, 2026\. This is a visual reference; check the library's license before using its components.
``````

## AI skill detail

GET `/ai-skills/00000000-0000-0000-0000-000000000003/` with `Accept: text/markdown`

Status: 200. Content-Type: `text/markdown; charset=utf-8`. Vary: `Cookie, Accept, HX-Request, HX-History-Restore-Request`.

``````markdown
[← AI skills](/ai-skills/)

# Typography skill

Review hierarchy, spacing, and readable line lengths.

typography review

[View skill source ↗](https://example.com/skill)

GitHub stars: not checked

skills.sh installs: not checked

## Compatible agents

Claude Code Codex

## Installation

```
npx skills add example/design
```

Review the source and instructions before installing in your agent.

## License

Not confirmed. Check the source for usage terms.
``````

## Documentation

GET `/docs/getting-started/introduction/` with `Accept: text/markdown`

Status: 200. Content-Type: `text/markdown; charset=utf-8`. Vary: `Cookie, Accept, HX-Request, HX-History-Restore-Request`.

``````markdown
# Find your next design reference

TastefulKit is a library of real landing-page screenshots. Use it to find examples of layouts, typography, colors, and spacing, then save the ones you want to revisit.

## Take a first look

Try the [Design Arena](/arena/) and browse the [global rankings](/rankings/) for free without an account. Sign in to start building your own taste profile.

Explore, full screenshots, and available DESIGN.md guides are public: you can browse, view, copy, and download without signing in. A free account is needed for saved designs and personal rankings. API/MCP access also requires your personal API key. No subscription is required.

1. Open [Explore](/explore/) to browse the library, newest first.
2. Search for a description such as `minimal landing page with bold typography`.
3. Open a result to see its full screenshot and visit the original website.
4. To keep a shortlist, [create an account](/accounts/signup/) and confirm your email.
5. Choose **Save design \+** to keep it in your **Saved** list.

## Choose a guide

* [Browse and inspect designs](/docs/using-tastefulkit/browsing/) — understand screenshots, tags, and source links.
* [Search and filter](/docs/using-tastefulkit/search/) — narrow a visual idea into useful references.
* [Save designs](/docs/using-tastefulkit/saved-designs/) — build and search your personal shortlist.
* [Manage your account](/docs/getting-started/account/) — email confirmation, sign-in, and API keys.
* [Use the API](/docs/api-reference/introduction/) — read catalogue results from a script or agent.

## Use references thoughtfully

Screenshots are inspiration, not downloadable website templates or a license to reuse someone else's design or assets. Study the choices that make an example work, then apply those ideas to your own project.

[Next → Your account](/docs/getting-started/account/)
``````
