from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
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


def paid_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not has_paid_access(request.user):
            return redirect("pricing")
        response = view(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    return wrapped
