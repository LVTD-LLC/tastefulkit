import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.billing.access import has_paid_access
from apps.billing.models import BillingAccount
from apps.billing.services import handle_event, portal_url, refresh_user
from apps.billing.stripe_api import BillingUnavailable, client

logger = logging.getLogger(__name__)
BILLING_ERRORS = (stripe.StripeError, BillingUnavailable)


def unavailable(request):
    logger.warning("billing.request.failed", extra={"event.name": "billing.request.failed"})
    messages.error(request, "Billing is temporarily unavailable. Please try again shortly.")
    return redirect("pricing")


@never_cache
def pricing(request):
    account = (
        BillingAccount.objects.filter(user=request.user).first()
        if request.user.is_authenticated
        else None
    )
    return render(
        request,
        "billing/pricing.html",
        {
            "billing_account": account,
        },
    )


@login_required
@require_POST
@never_cache
def checkout(request):
    messages.info(request, "All current TastefulKit features are free. No subscription is needed.")
    return redirect("library")


@login_required
@require_POST
@never_cache
def portal(request):
    try:
        with transaction.atomic():
            account = BillingAccount.objects.select_for_update().filter(user=request.user).first()
            if not account or not account.customer_id:
                return redirect("pricing")
            return redirect(portal_url(account, client()))
    except BILLING_ERRORS:
        return unavailable(request)


@login_required
@never_cache
def billing_return(request):
    try:
        refresh_user(request.user)
    except BILLING_ERRORS:
        return unavailable(request)
    if has_paid_access(request.user):
        return redirect("library")
    messages.info(request, "Billing status refreshed. All current features are free.")
    return redirect("pricing")


EVENT_TYPES = {
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
}


@csrf_exempt
@require_POST
def webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=503)
    if len(request.body) > 1_000_000:
        return HttpResponse(status=413)
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.headers.get("Stripe-Signature", ""),
            settings.STRIPE_WEBHOOK_SECRET,
        )
        if event["type"] in EVENT_TYPES:
            handle_event(event)
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)
    except BILLING_ERRORS:
        logger.warning("billing.webhook.failed", extra={"event.name": "billing.webhook.failed"})
        return HttpResponse(status=503)  # Stripe retries; never mark failed events processed.
    return HttpResponse(status=200)
