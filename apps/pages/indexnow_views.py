from django.conf import settings
from django.http import HttpResponse
from django.utils.crypto import salted_hmac
from django.views.decorators.http import require_safe


@require_safe
def indexnow_key(request):
    # Domain-separated HMAC exposes only a verification value, never SECRET_KEY.
    key = salted_hmac(
        "tastefulkit.indexnow", settings.SITE_URL.rstrip("/"), algorithm="sha256"
    ).hexdigest()
    response = HttpResponse(key, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "no-store"
    response["X-Robots-Tag"] = "noindex"
    response["X-Deployment-Revision"] = settings.DEPLOYMENT_REVISION
    return response
