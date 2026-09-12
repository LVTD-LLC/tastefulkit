from django.urls import path

from apps.catalogue import views

urlpatterns = [
    path("explore/", views.library, name="library"),
    path("designs/<uuid:pk>/", views.detail, name="design_detail"),
    path("designs/<uuid:pk>/save/", views.save_design, name="save_design"),
]
