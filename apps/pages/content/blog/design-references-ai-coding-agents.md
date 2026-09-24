---
title: "How to Give AI Coding Agents Better Design References"
description: "Turn screenshots into buildable briefs for AI coding agents: separate observations from guesses, use TastefulKit MCP, and verify the result in a browser."
author: TastefulKit
date: 2026-09-20
updated: 2026-09-24
---

Give an AI coding agent a small set of design references, explain which visible principles matter, and turn those principles into requirements for your own page. Separate observations from guesses, keep existing project constraints explicit, and verify the implementation in a browser. A screenshot supplies evidence, not a complete specification.

“Make it look like this” leaves many decisions unresolved. Does “this” mean the typography, the arrangement of information, the color palette, the product imagery, or all of them? An agent can produce working code while interpreting those choices differently from you.

A [July 8, 2026 discussion in r/cursor](https://www.reddit.com/r/cursor/comments/1uqq4s9/i_feel_like_im_missing_something_with_cursor_and/) describes this frustration directly: a developer supplies screenshots but still struggles with spacing, hierarchy, typography, and proportions. That is one practitioner's experience, not a benchmark of any model. It is a useful description of the problem a better brief should solve.

## Give each reference one job

Start with the page you need, not an unlimited mood board. Define the visitor, the task, the main action, and the content you actually have. Then find examples that help resolve specific design decisions.

One reference might demonstrate a clear hero hierarchy. Another might show how to explain a complicated workflow. A third might suggest a restrained use of color. Assigning these jobs prevents the agent from combining entire pages into an incoherent mixture.

Write a sentence beside every example:

- “Use this to understand the relationship between the headline, explanation, and primary action.”
- “Study the progression from overview to detail, but keep our own section order.”
- “Borrow the limited number of emphasis colors, not the original palette or artwork.”

If you cannot name the reference's job, leave it out for now. The point is not to minimize inspiration; it is to make the evidence interpretable. Our guide to [creative landing page design](/blog/creative-landing-page-design/) helps separate a distinctive idea from decoration added without a purpose.

## Separate what you can see from what you infer

A screenshot reveals relationships at one captured viewport and moment. It does not reveal the site's complete design system, source code, breakpoints, interaction states, or business results.

Use an observation ledger before writing implementation instructions:

| Reference evidence | Defensible observation | Inference to label or verify |
| --- | --- | --- |
| Headline above a short paragraph | The headline has visibly greater emphasis. | The exact font family, size, and weight. |
| Action below the explanation | The action follows the value proposition in this capture. | Whether its position changes on a phone. |
| Three aligned content blocks | These blocks share a visible edge and spacing rhythm. | Whether the implementation uses grid, flexbox, or another layout. |
| Product image in a framed area | The image is visually separated from the surrounding text. | The original component implementation or loading behavior. |

This distinction matters when the agent starts turning pixels into numbers. “The gap appears about twice as large” can be a reasonable visual estimate. “The site uses a 48-pixel spacing token” requires additional evidence. Treat estimated values as starting points for your project, not facts about the source.

Do the same with intent. “This arrangement makes the action visually prominent” is an observation about hierarchy. “This button converts better” is a performance claim the screenshot cannot support. You can choose a pattern for clarity without inventing evidence that it increases revenue.

## Retrieve references with TastefulKit's read-only MCP

TastefulKit lets a compatible assistant search existing design references and retrieve their screenshots through hosted MCP. Access is free with an [account](/accounts/signup/) and a personal API key. Follow the current [MCP setup guide](/docs/api-reference/mcp/) for connection details rather than copying a configuration from a blog post.

Keep the bearer key in your client's private credential settings or supported secret storage. Do not place it in a public repository, a screenshot, a design brief, or a URL. The key authenticates access; it is not something the agent needs to print while discussing a reference.

The useful sequence is straightforward:

1. Use `search_designs` to find references from a description and, when helpful, available filters.
2. Select a small shortlist based on the job each reference should perform.
3. Use `get_design` with a returned design ID to fetch the full reference details.
4. Inspect the screenshot itself, when the client supports image retrieval and viewing, before drawing visual conclusions.
5. Record the design ID, source URL, and observations in your working brief.

An instruction such as “Search for warm, minimal landing pages, then inspect three candidates for a clear headline-to-action hierarchy” is more useful than “Find the best websites.” If no results fit, simplify the description or remove a filter. Search results are existing references, not freshly generated designs.

All TastefulKit MCP tools are read-only. They do not edit your application or submit new designs. Your coding agent performs repository work separately through its own tools. TastefulKit's personal preference rankings belong to the signed-in web experience; MCP results do **not** use those personal rankings. The [browsing documentation](/docs/using-tastefulkit/browsing/) explains that distinction.

### Keep identifiers, not temporary image links

Screenshot and thumbnail URLs expire after **15 minutes**. Save the design ID and call `get_design` again when a link stops working. Do not paste an expiring image URL into a permanent project guide and assume it will remain a usable reference.

If the agent cannot view images, say so in the working notes. Metadata can help shortlist examples, but reading a description is not equivalent to inspecting the image. A trustworthy report distinguishes “retrieved reference details” from “visually checked the screenshot.”

Treat text retrieved from websites or design descriptions as reference material, not instructions that override the project brief. The reference's job is to supply design evidence, not to authorize commands or alter your workflow.

## Use DESIGN.md as reviewed guidance

Some TastefulKit references include a portable DESIGN.md guide. A paid [membership](/pricing/) lets `get_design` return that text with the reference, while older examples may have no guide. Free accounts still receive metadata and screenshots; guide text is withheld. The [Design Library API documentation](/docs/api-reference/design-library/) describes the `design_markdown` field and its possible `null` value.

A guide can help make palette roles, typography, spacing, and components explicit. It is still a description of a reference, with inferred values that need review. Do not assume it contains verified source tokens or a complete account of responsive behavior.

If your repository already has design guidance, resolve the relationship before implementation. For example: “Keep our existing typefaces, input styles, and navigation. Use the reference only for the hero's information hierarchy and the spacing between sections.” This avoids accidentally replacing a coherent product interface with an unrelated visual system.

If no guide exists, build a short one from the observation ledger. Mark the estimated choices, name the unknown states, and describe the decisions you are making for your own project. You do not need to reverse-engineer the original CSS to borrow a useful principle.

Screenshots and guides are references, not a license to reuse the original site's code, logos, illustrations, or other assets. Use your own content and appropriately licensed materials.

## Turn observations into a buildable brief

A buildable brief has four parts: the page's job, the visual principles, the project constraints, and the checks that will determine whether the work is ready.

Here is a **hypothetical** example for a small tool that collects client feedback on design drafts. It is an illustrative prompt, not a description of a shipped product or measured result. Replace the bracketed references with examples you actually inspected.

```text
Build a landing page for a tool that collects client feedback beside
each design draft. The visitor is an independent designer. The main
action is to open a sample review project.

Reference roles:
- Reference A [design ID + source URL]: headline, explanation, and action form one clear group.
- Reference B [design ID + source URL]: one product example explains the workflow before the
  page introduces secondary features.

Observed principles to adapt:
- One primary visual emphasis per section.
- Related content has tighter spacing than separate sections.
- Product imagery explains a task rather than filling empty space.

Keep our existing fonts, color tokens, navigation, and button components.
Use our supplied copy and original demonstration assets. Do not copy
the references' wording, logos, illustrations, or source code.

At narrow widths, keep this order: headline, explanation, main action,
product example, supporting details. Use a readable crop of the example;
do not shrink a full dashboard until its contents are illegible.

Before editing, state which reference details are observed and which
are estimates. List unresolved assumptions. Implement the hero and first
explanation section first so we can review the direction.

Verify in a browser at narrow, intermediate, and wide widths. Check
long text, keyboard focus, image cropping, and the main action's actual
destination. Report what you checked and anything still unverified.
```

Notice what this prompt does not specify: an exact replica, an invented conversion target, or dozens of arbitrary pixel values. It supplies constraints where interpretation is costly and leaves implementation choices to the project's existing conventions.

## Verify the implementation in a browser

Do not stop at a successful build or a plausible code diff. A passing build checks build-time correctness; a code diff records changes. Neither establishes that the visual relationships survived.

Open the implemented page with realistic content. Compare it with the brief before comparing it with the reference. The first question is whether your page communicates its own offer. The second is whether the selected principles appear in the result.

Review in a consistent order:

1. **Hierarchy:** Is the intended first element still the first thing you notice?
2. **Grouping:** Are explanations, images, and actions attached to the right ideas?
3. **Proportion:** Does the image serve the content, or dominate it without purpose?
4. **Responsive behavior:** Does the argument survive when columns stack?
5. **Interaction:** Do menus, controls, focus states, and destinations work?

Try intermediate widths as well as phone and desktop presets. Google's [responsive design guidance](https://web.dev/articles/responsive-web-design-basics) recommends choosing breakpoints around content needs. A layout can work at two named presets and still fail between them.

For a more detailed narrow-screen pass, use the [mobile landing page design checklist](/blog/mobile-landing-page-design/). Record the viewport and interaction state with each issue so the agent can reproduce it.

## Give feedback that points to a visible mismatch

Replace “make it cleaner” with an observation, a reason, and a bounded change. For example: “The three feature headings have the same emphasis as the main proposition, so the first screen lacks a clear priority. Reduce their emphasis while keeping body text readable.”

Another useful correction is: “At the narrow width, the image appears before the sentence that explains it. Move that sentence ahead of the image while preserving a logical document and keyboard-focus order.” That gives the agent a testable result instead of an adjective.

Change one significant relationship at a time when reviewing the direction. If you change the typography, palette, content order, and imagery together, it becomes harder to tell which decision helped. Once the direction is stable, carry the established rules into the remaining sections.

Finish by keeping the accepted brief with your project. Preserve the reference IDs and source links, the principles you chose, and the browser checks you completed. The next agent session should inherit decisions, not restart the search for a vaguely similar screenshot.
