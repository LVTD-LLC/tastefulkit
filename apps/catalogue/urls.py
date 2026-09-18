from django.urls import path

from apps.catalogue import arena_views, views

urlpatterns = [
    path("arena/", arena_views.voting_arena, name="voting_arena"),
    path("arena/vote/", arena_views.vote, name="arena_vote"),
    path("arena/revisit/", arena_views.revisit_skipped, name="arena_revisit"),
    path("rankings/", arena_views.rankings, name="design_rankings"),
    path("rankings/reset/", arena_views.reset_taste, name="reset_taste"),
    path("explore/", views.library, name="library"),
    path("designs/<uuid:pk>/", views.detail, name="design_detail"),
    path("designs/<uuid:pk>/DESIGN.md", views.design_markdown, name="design_markdown"),
    path("designs/<uuid:pk>/save/", views.save_design, name="save_design"),
]
