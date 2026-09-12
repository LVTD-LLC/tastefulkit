from django.contrib import admin

from apps.catalogue.models import Design, SavedDesign, Tag
from apps.catalogue.services import queue_capture


@admin.register(Design)
class DesignAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "capture_status", "published", "created_at"]
    list_filter = ["kind", "capture_status", "published"]
    search_fields = ["title", "source_url", "description"]
    filter_horizontal = ["tags"]
    readonly_fields = [
        "id",
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
    actions = ["retry_capture"]

    def has_add_permission(self, request):
        return False  # Use validated API submission for URL identity and capture queuing.

    @admin.action(description="Retry failed or queued captures")
    def retry_capture(self, request, queryset):
        for design in queryset.filter(capture_status__in=["pending", "failed"]):
            queue_capture(design.pk)


admin.site.register(Tag)
admin.site.register(SavedDesign)
