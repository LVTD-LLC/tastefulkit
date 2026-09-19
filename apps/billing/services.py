import uuid
from datetime import UTC, datetime

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.billing.models import BillingAccount, WebhookEvent
from apps.billing.stripe_api import BillingUnavailable, client


def site_url(name):
    return settings.SITE_URL.rstrip("/") + reverse(name)


def customer_subscriptions(account, api):
    result = api.v1.subscriptions.list(
        {"customer": account.customer_id, "status": "all", "limit": 100}
    )
    if result.get("has_more"):
        raise BillingUnavailable("Subscription reconciliation needs attention.")
    return result["data"]


def sync_account(account, api):
    """Caller holds the account row lock; reconcile current state, not event snapshots."""
    subscriptions = customer_subscriptions(account, api)
    matching = [
        sub
        for sub in subscriptions
        if sub.get("livemode") == settings.STRIPE_LIVE_MODE
        and any(item["price"]["id"] == settings.STRIPE_PRICE_ID for item in sub["items"]["data"])
    ]
    active = [sub for sub in matching if sub["status"] == "active"]
    chosen = max(active or matching, key=lambda sub: sub.get("created", 0), default=None)
    account.subscription_id = chosen["id"] if chosen else ""
    account.status = chosen["status"] if chosen else ""
    account.cancel_at_period_end = bool(chosen and chosen.get("cancel_at_period_end"))
    # Basil models billing periods per subscription item. Keep legacy snapshots readable.
    period_ends = (
        [
            item.get("current_period_end", chosen.get("current_period_end", 0))
            for item in chosen["items"]["data"]
            if item["price"]["id"] == settings.STRIPE_PRICE_ID
        ]
        if chosen and chosen["status"] == "active"
        else []
    )
    account.paid_until = datetime.fromtimestamp(max(period_ends), UTC) if period_ends else None
    account.save()
    return subscriptions


def portal_url(account, api):
    params = {"customer": account.customer_id, "return_url": site_url("pricing")}
    if settings.STRIPE_PORTAL_CONFIGURATION_ID:
        params["configuration"] = settings.STRIPE_PORTAL_CONFIGURATION_ID
    return api.v1.billing_portal.sessions.create(params)["url"]


def checkout_url(user):
    api = client()
    # Persist the attempt before any external request. Retries after timeouts use the same key.
    account, _ = BillingAccount.objects.get_or_create(user=user)
    with transaction.atomic():
        account = BillingAccount.objects.select_for_update().get(pk=account.pk)
        if not account.customer_id:
            customer = api.v1.customers.create(
                {"email": user.email, "metadata": {"tastefulkit_user_id": str(user.pk)}},
                options={"idempotency_key": f"customer-{account.checkout_attempt}"},
            )
            account.customer_id = customer["id"]
            account.save()
    # Commit customer ownership before creating a session that could emit webhooks.
    with transaction.atomic():
        account = BillingAccount.objects.select_for_update().get(pk=account.pk)
        subscriptions = sync_account(account, api)
        if any(sub["status"] not in {"canceled", "incomplete_expired"} for sub in subscriptions):
            return portal_url(account, api)
        if account.checkout_id:
            session = api.v1.checkout.sessions.retrieve(account.checkout_id)
            if session["status"] == "open":
                return session["url"]
            if session["status"] == "complete" and not any(
                sub["id"] == session.get("subscription")
                and sub["status"] in {"canceled", "incomplete_expired"}
                for sub in subscriptions
            ):
                # A completion can arrive before list reconciliation; never sell twice.
                return portal_url(account, api)
            account.checkout_id = ""
            account.checkout_attempt = uuid.uuid4()
            account.save()
    with transaction.atomic():
        account = BillingAccount.objects.select_for_update().get(pk=account.pk)
        session = api.v1.checkout.sessions.create(
            {
                "mode": "subscription",
                "customer": account.customer_id,
                "client_reference_id": str(user.pk),
                "line_items": [{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
                "subscription_data": {"metadata": {"tastefulkit_user_id": str(user.pk)}},
                "success_url": site_url("billing_return"),
                "cancel_url": site_url("pricing") + "?checkout=canceled",
            },
            options={"idempotency_key": f"checkout-{account.checkout_attempt}"},
        )
        account.checkout_id = session["id"]
        account.save()
        return session["url"]


def refresh_user(user):
    with transaction.atomic():
        account = BillingAccount.objects.select_for_update().filter(user=user).first()
        if account and account.customer_id:
            sync_account(account, client())
        return account


def handle_event(event):
    if event.get("livemode") != settings.STRIPE_LIVE_MODE:
        raise ValueError("Unexpected Stripe mode")
    context = event.get("context") or event.get("account")
    if context and context != settings.STRIPE_ACCOUNT_ID:
        raise ValueError("Unexpected Stripe account")
    obj = event["data"]["object"]
    customer_id = obj.get("customer")
    if not customer_id:
        return
    with transaction.atomic():
        account = BillingAccount.objects.select_for_update().filter(customer_id=customer_id).first()
        if not account or WebhookEvent.objects.filter(pk=event["id"]).exists():
            return
        sync_account(account, client())
        WebhookEvent.objects.create(id=event["id"])


def cancel_for_deletion(user):
    """Do not orphan recurring charges or an open Checkout when an account is deleted."""
    with transaction.atomic():
        account = BillingAccount.objects.select_for_update().filter(user=user).first()
        if not account or not account.customer_id:
            return
        api = client()
        for subscription in customer_subscriptions(account, api):
            if subscription["status"] not in {"canceled", "incomplete_expired"}:
                api.v1.subscriptions.cancel(subscription["id"])
        if account.checkout_id:
            session = api.v1.checkout.sessions.retrieve(account.checkout_id)
            if session["status"] == "open":
                api.v1.checkout.sessions.expire(account.checkout_id)
        account.status = "canceled"
        account.paid_until = timezone.now()
        account.save()
