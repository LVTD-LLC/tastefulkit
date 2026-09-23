"""Public error responses that do not depend on optional application context."""

from django.http import HttpResponseNotFound
from django.template.loader import render_to_string


def page_not_found(request, exception):
    # Do not pass request: RequestContext runs database-backed marketing/auth
    # processors, which must not turn a missing page into a server error.
    return HttpResponseNotFound(render_to_string("404.html"))
