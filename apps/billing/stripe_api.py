"""One pinned, server-only Stripe account; no module-global credential mutation."""

import stripe
from django.conf import settings


class BillingUnavailable(Exception):
    pass


def configured():
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PRICE_ID)


def client():
    if not configured():
        raise BillingUnavailable("Billing is not configured.")
    return stripe.StripeClient(
        settings.STRIPE_SECRET_KEY,
        stripe_version="2025-03-31.basil",
        stripe_context=settings.STRIPE_ACCOUNT_ID or None,
        max_network_retries=2,
        http_client=stripe.HTTPXClient(timeout=15, allow_sync_methods=True),
    )
