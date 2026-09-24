from django.utils import timezone

from apps.billing.models import BillingAccount


def has_paid_access(user):
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True  # Keep explicitly provisioned ingestion/moderation accounts operational.
    return BillingAccount.objects.filter(
        user=user, status="active", paid_until__gt=timezone.now()
    ).exists()
