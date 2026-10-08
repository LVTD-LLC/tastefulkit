"""Public newsletter signup; Listmonk owns consent and subscription state."""

import requests
from django import forms
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.crypto import salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods


def submission_allowed(request):
    # Only enable behind CapRover, which overwrites X-Real-IP.
    identity = request.META.get("REMOTE_ADDR", "")
    if settings.NEWSLETTER_TRUST_PROXY:
        identity = request.META.get("HTTP_X_REAL_IP", identity)
    key = "newsletter:" + salted_hmac("newsletter-rate", identity, algorithm="sha256").hexdigest()
    try:
        if cache.add(key, 1, timeout=3600):
            return True
        return cache.incr(key) <= 10
    except Exception:
        # Fail closed if the shared limiter is unavailable; never log identity.
        return False


def context(request):
    return {"newsletter_enabled": enabled(), "newsletter_form": NewsletterForm()}


class NewsletterForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "you@example.com",
                "aria-describedby": "newsletter-consent",
            }
        ),
    )
    company = forms.CharField(required=False, widget=forms.HiddenInput)


def enabled():
    return bool(settings.NEWSLETTER_LISTMONK_URL and settings.NEWSLETTER_LIST_UUID)


@never_cache
@require_http_methods(["GET", "POST"])
def subscribe(request):
    form = NewsletterForm(request.POST if request.method == "POST" else None)
    context = {"form": form}
    status = 200
    if not enabled():
        context["service_error"] = True
        status = 503
    elif request.method == "POST":
        if not submission_allowed(request):
            context["rate_limited"] = True
            response = render(request, "pages/newsletter.html", context, status=429)
            response["Retry-After"] = "3600"
            return response
        if form.is_valid():
            if form.cleaned_data["company"]:
                return redirect("newsletter_thanks")
            try:
                response = requests.post(
                    settings.NEWSLETTER_LISTMONK_URL.rstrip("/") + "/api/public/subscription",
                    json={
                        "email": form.cleaned_data["email"],
                        "list_uuids": [settings.NEWSLETTER_LIST_UUID],
                    },
                    timeout=(3, 10),
                    allow_redirects=False,
                )
                payload = response.json() if response.status_code == 200 else None
                data = payload.get("data") if isinstance(payload, dict) else None
                if not isinstance(data, dict) or not isinstance(data.get("has_optin"), bool):
                    raise ValueError("Unexpected newsletter response")
            except (requests.RequestException, ValueError):
                # Never log submitted addresses, provider response bodies, or exceptions.
                context["service_error"] = True
                status = 503
            else:
                return redirect("newsletter_thanks")
        else:
            status = 400
    return render(request, "pages/newsletter.html", context, status=status)


@never_cache
@require_GET
def thanks(request):
    return render(request, "pages/newsletter_thanks.html")
