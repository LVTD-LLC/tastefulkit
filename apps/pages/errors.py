"""Public error responses that do not depend on optional application context."""

from django.http import HttpResponseNotFound
from django.template.loader import render_to_string
from django.views.decorators.vary import vary_on_headers


@vary_on_headers("Accept")
def page_not_found(request, exception):
    # HTML wins wildcard preferences, preserving ordinary browser behavior.
    if request.get_preferred_type(["text/html", "text/markdown"]) == "text/markdown":
        return HttpResponseNotFound(
            "# 404 — Page not found\n\n"
            "The requested page could not be found on TastefulKit. "
            "Check the URL or use these resources to find an available page:\n\n"
            "- [Documentation](/docs/)\n"
            "- [Sitemap](/sitemap.xml)\n",
            content_type="text/markdown; charset=utf-8",
        )
    # Do not pass request: RequestContext runs database-backed marketing/auth
    # processors, which must not turn a missing page into a server error.
    return HttpResponseNotFound(render_to_string("404.html"))
