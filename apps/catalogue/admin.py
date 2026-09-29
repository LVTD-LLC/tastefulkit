from django.contrib import admin

from apps.catalogue.models import Design, SavedDesign, Site, Tag


@admin.register(Design)
class DesignAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "site", "capture_status", "published", "created_at"]
    list_filter = ["kind", "capture_status", "published"]
    search_fields = ["title", "source_url", "description"]
    autocomplete_fields = ["site"]
    readonly_fields = [
        "id",
        "title",
        "description",
        "industry",
        "tags",
        "design_markdown",
        "submitted_by",
        "fingerprint",
        "source_url",
        "kind",
        "selector",
        "viewport_width",
        "screenshot",
        "thumbnail",
        "capture_status",
        "embedding",
        "embedding_model",
        "capture_error",
        "embedding_error",
        "captured_at",
        "processing_at",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False  # Complete prepared designs enter only through the admin POST.


admin.site.register(Tag)
admin.site.register(SavedDesign)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ["name", "url"]
    search_fields = ["name", "url"]
    readonly_fields = ["url"]

    def has_add_permission(self, request):
        return False
