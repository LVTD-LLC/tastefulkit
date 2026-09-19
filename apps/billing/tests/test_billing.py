import hashlib
import hmac
import json
import time
from datetime import timedelta
from unittest.mock import Mock

import pytest
import stripe
from django.contrib.auth.models import AnonymousUser
from django.test import Client
from django.utils import timezone

from apps.billing import services
from apps.billing.access import has_paid_access
from apps.billing.models import BillingAccount, WebhookEvent
from apps.billing.stripe_api import BillingUnavailable

pytestmark = pytest.mark.django_db


@pytest.fixture
def billing_settings(settings):
    settings.STRIPE_SECRET_KEY = "sk_test_not_a_real_key"
    settings.STRIPE_PRICE_ID = "price_membership"
    settings.STRIPE_ACCOUNT_ID = "acct_test"
    settings.STRIPE_WEBHOOK_SECRET = "local-test-signing-secret"
    settings.STRIPE_LIVE_MODE = False
    settings.SITE_URL = "https://testserver"
    return settings


@pytest.fixture
def api(monkeypatch, billing_settings):
    api = Mock()
    api.v1.customers.create.return_value = {"id": "cus_local"}
    api.v1.subscriptions.list.return_value = {"data": [], "has_more": False}
    api.v1.checkout.sessions.create.return_value = {
        "id": "cs_local",
        "status": "open",
        "url": "https://checkout.stripe.com/test",
    }
    api.v1.checkout.sessions.retrieve.return_value = api.v1.checkout.sessions.create.return_value
    api.v1.billing_portal.sessions.create.return_value = {"url": "https://billing.stripe.com/test"}
    monkeypatch.setattr(services, "client", lambda: api)
    monkeypatch.setattr("apps.billing.views.client", lambda: api)
    return api


def subscription(status="active", price="price_membership", **overrides):
    return {
        "id": "sub_local",
        "customer": "cus_local",
        "status": status,
        "created": 1,
        "current_period_end": int(time.time()) + 3600,
        "cancel_at_period_end": False,
        "livemode": False,
        "items": {"data": [{"price": {"id": price}}]},
        **overrides,
    }


def signed_event(
    client, settings, *, event_id="evt_local", customer="cus_local", timestamp=None, **overrides
):
    timestamp = int(time.time()) if timestamp is None else timestamp
    payload = json.dumps(
        {
            "id": event_id,
            "type": "customer.subscription.updated",
            "livemode": False,
            "data": {"object": {"id": "sub_local", "customer": customer}},
            **overrides,
        }
    ).encode()
    digest = hmac.new(
        settings.STRIPE_WEBHOOK_SECRET.encode(),
        str(timestamp).encode() + b"." + payload,
        hashlib.sha256,
    ).hexdigest()
    return client.post(
        "/billing/webhook/",
        payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={digest}",
    )


def test_free_users_can_vote_but_cannot_read_catalog_or_agent_setup(client, user):
    key = user.profile.rotate_api_key()
    assert client.get("/arena/").status_code == 200
    assert client.get("/pricing/").status_code == 200
    for path in [
        "/explore/",
        "/home",
        "/rankings/",
        "/rankings/?mode=personal",
        "/docs/api-reference/mcp/",
        "/designs/00000000-0000-0000-0000-000000000001/",
        "/designs/00000000-0000-0000-0000-000000000001/DESIGN.md",
    ]:
        assert "/accounts/login/" in client.get(path).url
    client.force_login(user)
    for path in [
        "/explore/",
        "/home",
        "/rankings/",
        "/rankings/?mode=personal",
        "/docs/api-reference/mcp/",
    ]:
        assert client.get(path).url == "/pricing/"
    assert client.post("/settings/api-key/rotate/").url == "/pricing/"
    assert client.post("/rankings/reset/").url == "/pricing/"
    assert client.get("/settings").status_code == 200
    assert b"Generate API key" not in client.get("/settings").content
    for path in [
        "/api/user",
        "/api/v1/designs",
        "/api/v1/designs/00000000-0000-0000-0000-000000000001",
    ]:
        response = client.get(path, HTTP_AUTHORIZATION=f"Bearer {key}")
        assert response.status_code == 402
        assert "membership" in response.json()["detail"]


@pytest.mark.parametrize(
    "status", ["", "trialing", "past_due", "unpaid", "canceled", "incomplete", "paused"]
)
def test_only_current_active_subscriptions_grant_access(user, status):
    BillingAccount.objects.create(
        user=user, status=status, paid_until=timezone.now() + timedelta(days=30)
    )
    assert not has_paid_access(user)
    assert not has_paid_access(AnonymousUser())


def test_expiration_and_inactive_accounts_fail_closed(paid_user):
    assert has_paid_access(paid_user)
    BillingAccount.objects.filter(user=paid_user).update(
        paid_until=timezone.now() - timedelta(seconds=1)
    )
    assert not has_paid_access(paid_user)
    paid_user.is_superuser = True
    assert has_paid_access(paid_user)
    paid_user.is_active = False
    assert not has_paid_access(paid_user)


def test_checkout_is_post_only_csrf_protected_and_uses_server_plan(user, api, auth_client):
    assert auth_client.get("/billing/checkout/").status_code == 405
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(user)
    assert csrf.post("/billing/checkout/").status_code == 403
    for _ in range(2):
        response = auth_client.post(
            "/billing/checkout/",
            {"price": "price_free", "customer": "cus_attacker", "next": "https://evil.test"},
        )
        assert response.url == "https://checkout.stripe.com/test"
    api.v1.customers.create.assert_called_once()
    api.v1.checkout.sessions.create.assert_called_once()
    payload = api.v1.checkout.sessions.create.call_args.args[0]
    assert payload["customer"] == "cus_local"
    assert payload["line_items"] == [{"price": "price_membership", "quantity": 1}]
    assert payload["success_url"] == "https://testserver/billing/return/"
    assert payload["mode"] == "subscription"
    assert "payment_method_types" not in payload  # Respect Managed Payments defaults.
    assert not has_paid_access(user)


def test_checkout_timeout_reuses_persisted_attempt(auth_client, api, user):
    api.v1.checkout.sessions.create.side_effect = stripe.APIConnectionError("timeout")
    assert auth_client.post("/billing/checkout/").url == "/pricing/"
    attempt = api.v1.checkout.sessions.create.call_args.kwargs["options"]["idempotency_key"]
    api.v1.checkout.sessions.create.side_effect = None
    assert auth_client.post("/billing/checkout/").url.startswith("https://checkout.stripe.com")
    assert api.v1.checkout.sessions.create.call_args.kwargs["options"]["idempotency_key"] == attempt
    assert BillingAccount.objects.get(user=user).customer_id == "cus_local"


def test_expired_checkout_starts_new_attempt_but_existing_subscription_opens_portal(
    auth_client, api, user
):
    auth_client.post("/billing/checkout/")
    first = BillingAccount.objects.get(user=user).checkout_attempt
    api.v1.checkout.sessions.retrieve.return_value = {"status": "expired"}
    auth_client.post("/billing/checkout/")
    assert BillingAccount.objects.get(user=user).checkout_attempt != first
    api.v1.subscriptions.list.return_value = {"data": [subscription("past_due")]}
    assert auth_client.post("/billing/checkout/").url == "https://billing.stripe.com/test"
    assert api.v1.checkout.sessions.create.call_count == 2


def test_return_cannot_claim_another_customer_or_trust_query_string(auth_client, user, api):
    assert (
        auth_client.get("/billing/return/?session_id=cs_someone_else&paid=true").url == "/pricing/"
    )
    assert not has_paid_access(user)
    BillingAccount.objects.create(user=user, customer_id="cus_local")
    api.v1.subscriptions.list.return_value = {"data": [subscription()]}
    assert auth_client.get("/billing/return/").url == "/explore/"
    assert has_paid_access(user)
    assert api.v1.subscriptions.list.call_args.args[0]["customer"] == "cus_local"


def test_signature_and_environment_rejections_do_not_change_access(
    client, user, api, billing_settings
):
    BillingAccount.objects.create(user=user, customer_id="cus_local")
    assert (
        client.post("/billing/webhook/", b"{}", content_type="application/json").status_code == 400
    )
    assert (
        signed_event(client, billing_settings, timestamp=int(time.time()) - 301).status_code == 400
    )
    assert signed_event(client, billing_settings, livemode=True).status_code == 400
    assert signed_event(client, billing_settings, account="acct_other").status_code == 400
    assert not WebhookEvent.objects.exists()
    api.v1.subscriptions.list.assert_not_called()


def test_webhooks_reconcile_current_state_idempotently_and_revoke(
    client, user, api, billing_settings
):
    BillingAccount.objects.create(user=user, customer_id="cus_local")
    api.v1.subscriptions.list.return_value = {"data": [subscription(cancel_at_period_end=True)]}
    assert signed_event(client, billing_settings).status_code == 200
    assert has_paid_access(user)
    assert BillingAccount.objects.get(user=user).cancel_at_period_end
    assert signed_event(client, billing_settings).status_code == 200
    assert api.v1.subscriptions.list.call_count == 1
    # An old creation event must not restore a currently canceled subscription.
    api.v1.subscriptions.list.return_value = {"data": [subscription("canceled")]}
    assert (
        signed_event(
            client, billing_settings, event_id="evt_old", type="customer.subscription.created"
        ).status_code
        == 200
    )
    assert not has_paid_access(user)
    assert WebhookEvent.objects.count() == 2


@pytest.mark.parametrize(
    "sub",
    [
        subscription(price="price_other"),
        subscription(livemode=True),
        subscription("past_due"),
        subscription("trialing"),
    ],
)
def test_wrong_plan_mode_or_status_cannot_unlock(client, user, api, billing_settings, sub):
    BillingAccount.objects.create(user=user, customer_id="cus_local")
    api.v1.subscriptions.list.return_value = {"data": [sub]}
    assert signed_event(client, billing_settings).status_code == 200
    assert not has_paid_access(user)


def test_retryable_webhook_failure_does_not_acknowledge_event(client, user, api, billing_settings):
    BillingAccount.objects.create(user=user, customer_id="cus_local")
    api.v1.subscriptions.list.side_effect = stripe.APIConnectionError("timeout")
    assert signed_event(client, billing_settings).status_code == 503
    assert not WebhookEvent.objects.exists()
    api.v1.subscriptions.list.side_effect = None
    api.v1.subscriptions.list.return_value = {"data": [subscription()]}
    assert signed_event(client, billing_settings).status_code == 200
    assert has_paid_access(user)
    assert (
        signed_event(
            client, billing_settings, customer="cus_other", event_id="evt_other"
        ).status_code
        == 200
    )
    assert WebhookEvent.objects.count() == 1


def test_deletion_cancels_billing_and_expires_open_checkout(auth_client, user, api):
    BillingAccount.objects.create(user=user, customer_id="cus_local", checkout_id="cs_local")
    api.v1.subscriptions.list.return_value = {"data": [subscription()]}
    auth_client.post("/delete-account/", {"confirmation": "DELETE"})
    api.v1.subscriptions.cancel.assert_called_once_with("sub_local")
    api.v1.checkout.sessions.expire.assert_called_once_with("cs_local")
    assert not type(user).objects.filter(pk=user.pk).exists()


def test_deletion_keeps_account_when_stripe_cannot_cancel(auth_client, user, api):
    BillingAccount.objects.create(user=user, customer_id="cus_local")
    api.v1.subscriptions.list.side_effect = BillingUnavailable("offline")
    assert auth_client.post("/delete-account/", {"confirmation": "DELETE"}).url == "/settings"
    assert type(user).objects.filter(pk=user.pk).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_checkout_requests_share_one_attempt(user, api):
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections

    BillingAccount.objects.create(user=user)

    def checkout(_):
        close_old_connections()
        try:
            return services.checkout_url(user)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        urls = list(pool.map(checkout, range(2)))
    assert urls == ["https://checkout.stripe.com/test"] * 2
    api.v1.customers.create.assert_called_once()
    keys = {
        call.kwargs["options"]["idempotency_key"]
        for call in api.v1.checkout.sessions.create.call_args_list
    }
    assert len(keys) == 1
    assert BillingAccount.objects.get(user=user).checkout_id == "cs_local"


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_webhooks_reconcile_once(user, api):
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections

    BillingAccount.objects.create(user=user, customer_id="cus_local")
    api.v1.subscriptions.list.return_value = {"data": [subscription()]}
    event = {
        "id": "evt_concurrent",
        "livemode": False,
        "data": {"object": {"customer": "cus_local"}},
    }

    def deliver(_):
        close_old_connections()
        try:
            services.handle_event(event)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(deliver, range(2)))
    api.v1.subscriptions.list.assert_called_once()
    assert WebhookEvent.objects.count() == 1
    assert has_paid_access(user)


def test_completed_checkout_waits_for_reconciliation_but_canceled_members_can_resubscribe(
    auth_client, user, api
):
    BillingAccount.objects.create(user=user, customer_id="cus_local", checkout_id="cs_old")
    api.v1.checkout.sessions.retrieve.return_value = {
        "status": "complete",
        "subscription": "sub_local",
    }
    assert auth_client.post("/billing/checkout/").url == "https://billing.stripe.com/test"
    api.v1.checkout.sessions.create.assert_not_called()
    api.v1.subscriptions.list.return_value = {"data": [subscription("canceled")]}
    assert auth_client.post("/billing/checkout/").url == "https://checkout.stripe.com/test"
    api.v1.checkout.sessions.create.assert_called_once()


def test_basil_subscription_item_period_controls_access(client, user, api, billing_settings):
    BillingAccount.objects.create(user=user, customer_id="cus_local")
    sub = subscription()
    end = sub.pop("current_period_end")
    sub["items"]["data"][0]["current_period_end"] = end
    api.v1.subscriptions.list.return_value = {"data": [sub]}
    assert signed_event(client, billing_settings).status_code == 200
    account = BillingAccount.objects.get(user=user)
    assert int(account.paid_until.timestamp()) == end
    assert has_paid_access(user)
