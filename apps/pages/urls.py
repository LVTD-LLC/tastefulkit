from django.urls import path

from apps.catalogue.views import landing
from apps.pages import views

urlpatterns = [
    path("", landing, name="landing"),
    path("privacy-policy", views.PrivacyPolicyView.as_view(), name="privacy_policy"),
    path("terms-of-service", views.TermsOfServiceView.as_view(), name="terms_of_service"),
    path("docs/", views.docs_home_view, name="docs_home"),
    path("docs/<str:category>/<str:page>/", views.docs_page_view, name="docs_page"),
]
