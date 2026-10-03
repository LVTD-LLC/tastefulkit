<p align="center">
  <img src="frontend/static/brand/apple-touch-icon.png" alt="TastefulKit reference-stack logo" width="88" height="88">
</p>

<h1 align="center">TastefulKit</h1>

<p align="center"><strong>Find your taste. Build from it.</strong></p>

<p align="center">
  <a href="https://tastefulkit.com">Website</a> ·
  <a href="https://tastefulkit.com/docs/">Docs</a> ·
  <a href="https://tastefulkit.com/blog/">Blog</a> ·
  <a href="https://tastefulkit.com/docs/api-reference/mcp/">Connect your assistant</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

TastefulKit is a searchable library of real landing-page and component design examples for you and
your AI assistant. Find a layout, explore its typography and colors, and save
useful references for your next project.

## From an idea to a useful reference

“Minimal landing page with bold typography” is a starting point. TastefulKit
helps you turn it into examples you can actually look at, compare, and discuss.

- **Search in your own words.** Describe the style or page you have in mind.
- **Narrow the search.** Filter pages and components by type, style tag, industry, or source site.
- **Look beyond the thumbnail.** Open full screenshots, read descriptions, and
  visit the original websites.
- **Take a design direction with you.** View, copy or download an example’s DESIGN.md
  for free when available, or retrieve its text through MCP/API.
- **Keep a shortlist.** Save designs and revisit them when you're ready to build.
- **Bring your assistant.** Search and retrieve references through MCP or the API.

## Take a first look

Vote in the [Design Arena](https://tastefulkit.com/arena/) for free, with or without an account.
Lightweight previews appear first; full screenshots load in the background for scrolling.
Global rankings, the full catalog and design details are public too, including full screenshots and DESIGN.md downloads. The full catalog, personalized rankings, saved designs, screenshots, and API/MCP
access are free, including viewing, copying, downloading, and retrieving available
DESIGN.md guides. No subscription or credit card is required.
Signed-in votes shape your personal ranking;
guest votes count globally and are not transferred on signup.

1. Open [Explore](https://tastefulkit.com/explore/) to search and filter the full library without signing in.
2. Open a design to inspect its screenshot and design guide.
3. Create a free account when you want to save designs or personalize your rankings.

Start with the [browsing guide](https://tastefulkit.com/docs/using-tastefulkit/browsing/)
or learn how to [search and filter](https://tastefulkit.com/docs/using-tastefulkit/search/).

For practical reference workflows, read the free [landing page design guides](https://tastefulkit.com/blog/).
Blog articles are maintained in the repository; see [blog authoring](docs/blog-authoring.md) to contribute.

## Give your AI assistant something to work with

Connect a compatible assistant to TastefulKit's hosted MCP server using a personal
API key from your account. No local TastefulKit server is needed.

Then try:

> Find warm, minimal landing pages with strong typography. Show me three references
> with their screenshots and source links, and explain what makes each layout work.

Follow the [MCP connection guide](https://tastefulkit.com/docs/api-reference/mcp/)
for supported connection requirements and setup. Building your own integration?
See the [API guide](https://tastefulkit.com/docs/api-reference/introduction/).

## A reference library, not a template pack

TastefulKit helps you study real design choices. Screenshots belong to their
original creators; they are inspiration, not downloadable source code or a
license to reuse a site's assets.

Browsing, search, saved designs, and assistant access are available today.
Anyone can [compare designs](https://tastefulkit.com/arena/) and explore
[global Elo rankings](https://tastefulkit.com/rankings/) without signing in. Guest
votes contribute globally, with duplicate protection and a 30-action/minute limit
per browser session. Signed-in members can also build a private
[personal ranking](https://tastefulkit.com/rankings/?mode=personal) from their
votes and saved references. Guest votes stay global-only; they are not imported
into an account when you sign in. Clearing cookies starts a new guest session.

## Help make TastefulKit better

Bug reports, clear feature requests, documentation improvements, and focused
pull requests are welcome. [Open an issue](https://github.com/LVTD-LLC/tastefulkit/issues)
or read the [contribution guide](CONTRIBUTING.md).

For local development, architecture, and deployment, see [AGENTS.md](AGENTS.md)
and the [maintainer documentation](docs/maintainers/README.md).

## UI libraries

Browse the public [UI library directory](https://tastefulkit.com/ui-libraries/)
for screenshots, descriptions, framework notes, website/GitHub links and
researched pricing. Unknown pricing is labeled as unconfirmed. Library detail
pages are public; no account is needed. UI libraries are browse-only; Arena and rankings compare visual design references.
Read-only REST and MCP access continues to use an active account's API key.

Discovery pages share two navigation rows: Explore, Arena, Global ranking and For you, followed by content types. Visual reference types carry across sections. UI libraries and AI skills are Explore-only; entering Arena or rankings from these directories selects landing pages. UI libraries, AI skills and landing pages are always available in Explore; other types appear as published references are added. Explore defaults to landing pages and keeps saved references accessible below the tabs.

### Install skills into your agent

Sign in and use **Copy AI Tooling Installation Prompt** in the [How to Use guide](https://tastefulkit.com/how-to-use/).
The prompt includes your API key and the [public skills + MCP repository](https://github.com/LVTD-LLC/tastefulkit-skills).
Keep it private and paste it only into an agent you trust. New accounts receive a key automatically.
Rotation in Account settings revokes all previous keys.

Operator rollout: after both app services deploy, run `python manage.py provision_api_keys`.
The command is idempotent and prints counts only. Unrecoverable legacy keys stay valid
until explicit rotation. Recoverable keys are encrypted using a domain-separated key
from Django's `SECRET_KEY`; keep the previous secret in `SECRET_KEY_FALLBACKS` when
rotating it. Never discard those secrets until existing ciphertext is re-encrypted
or account keys are explicitly rotated. API authentication continues to use hashes.
The additive schema can be rolled back at the application layer without dropping fields,
but old application versions do not recognize preserved legacy credentials after provisioning.

### Design-focused AI skills

Browse `/ai-skills/` for agent skills covering interface design, accessibility, and
frontend workflows. Entries include source links, usage notes, compatible agents,
installation instructions and licensing where confirmed. The directory is public;
read-only REST list/detail endpoints at `/api/v1/ai-skills` require a free account's
API key. Skills are not installed or executed by TastefulKit and do not participate
in Arena or rankings. UI libraries also remain browse-only in Explore.

Use the header’s **Explore** menu for Designs (landing pages), UI libraries, AI skills, Docs and Blog. **Arena** opens design voting; rankings remain in discovery tabs. Open your username menu for Settings and Log out.

AI skill listings include source-linked GitHub repository stars and skills.sh
installs when checked. Sort by either popularity count or by name; unknown counts
appear last. Stars describe the whole repository, while installs describe the
specific skill. Checked dates show when each source was last verified.

### Public browsing

All Explore destinations are available without signing in: designs and components, UI libraries, AI skills, Docs and Blog. Published design details include full screenshots, related references and DESIGN.md downloads. Sign in only for saved collections, personalized rankings and your API/MCP key.

Start with the public [How to Use guide](https://tastefulkit.com/how-to-use/) for Explore, Arena and AI setup. Signed-in users can copy their personal AI tooling installation prompt there.

### Animated design references

Designs can include a short silent MP4 alongside their static screenshot. Explore's
**Has motion** filter finds them. Visible gallery previews play at most two clips
at once; reduced-motion and data-saver preferences disable automatic playback.
Use the Play/Pause button to control a preview, or open the design for native video
controls and **Motion / Screenshot** views. Arena continues comparing static images.

API/MCP list and search accept `has_motion=true`; responses include `video_url`,
`video_duration` (seconds), `video_width`, `video_height`, and `motion_notes`.
Asset links expire: fetch the reference again to refresh them. Motion notes and
DESIGN.md explain behavior for agents that cannot view video. Preparation and
replacement rules are in [the maintainer contract](docs/maintainers/design-ingestion.md#motion-previews).

### Navbar traffic counter

The shared navbar displays production pageviews in the rolling last 24 hours
(not unique people or sessions), sourced from PostHog. The worker refreshes the
Redis aggregate every five minutes; page rendering only reads the cache. A
measured zero is shown, while missing data or data older than 15 minutes is hidden.

Set `POSTHOG_PERSONAL_API_KEY` (read/query access), `POSTHOG_PROJECT_ID`, and
`POSTHOG_QUERY_HOST` on the worker only. Never replace the public capture token
`POSTHOG_API_KEY` with a personal key. After deploying, install the idempotent
schedule using `uv run python manage.py refresh_pageviews --schedule` and warm
the cache using `uv run python manage.py refresh_pageviews` in the worker.
The schedule persists across deploys; no startup or request-time queries run.
To disable, remove the named `navbar-pageviews` schedule or unset the worker
query credential; cached data expires within 15 minutes.
