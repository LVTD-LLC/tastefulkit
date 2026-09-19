import uuid

from django.conf import settings
from django.db import models


class BillingAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    subscription_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=40, blank=True)
    paid_until = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    checkout_id = models.CharField(max_length=255, blank=True)
    checkout_attempt = models.UUIDField(default=uuid.uuid4)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Billing account {self.pk}"


class WebhookEvent(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.pk
