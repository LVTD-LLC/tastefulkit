{% autoescape off %}# TastefulKit — Find your taste. Build from it.

Compare landing pages to rank designs around your taste. Give your coding agent the references to bring that look to your project.

## Explore

- [Explore designs]({% url 'library' %}): real website screenshots, components, motion previews where available, and DESIGN.md guides. Public browsing needs no account.
- [UI libraries]({% url 'ui_libraries' %}): discover component libraries, frameworks, and pricing information.
- [AI skills]({% url 'ai_skills' %}): discover design and UI-related skills and their source links.

## Arena and rankings

- [Vote on designs]({% url 'voting_arena' %}) to compare visual references side by side.
- [Global ranking]({% url 'design_rankings' %}) reflects community preferences. Sign in for personal rankings and saved designs.

## Top-ranked landing pages
{% for reference in references %}
- [{{ reference.title }}]({{ reference.url }}){% empty %}
We're collecting the first landing pages. A growing library of real-world inspiration is on its way.{% endfor %}

## Use with AI

Use screenshots and DESIGN.md guides as references for your coding agent. REST and MCP access require a free account and a personal API key.

- [How to Use]({% url 'how_to_use' %}): Explore, Arena, and AI tooling setup.
- [Documentation]({% url 'docs_home' %})
- [MCP connection guide](/docs/api-reference/mcp/)
- [Blog]({% url 'blog_index' %})
- [Sitemap](/sitemap.xml)
{% endautoescape %}
