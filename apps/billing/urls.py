from django.urls import path

from apps.billing import views

urlpatterns = [
    path("pricing/", views.pricing, name="pricing"),
    path("billing/checkout/", views.checkout, name="billing_checkout"),
    path("billing/portal/", views.portal, name="billing_portal"),
    path("billing/return/", views.billing_return, name="billing_return"),
    path("billing/webhook/", views.webhook, name="billing_webhook"),
]
