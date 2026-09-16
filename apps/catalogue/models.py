import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse


class Tag(models.Model):
    name = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Design(models.Model):
    class Kind(models.TextChoices):
        LANDING = "landing_page", "Landing page"
        PRICING = "pricing_page", "Pricing page"
        HERO = "hero", "Hero"
        BLOG = "blog", "Blog"
        NAVIGATION = "navigation", "Navigation"
        FOOTER = "footer", "Footer"
        DASHBOARD = "dashboard", "Dashboard"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Queued"
        PROCESSING = "processing", "Capturing"
        READY = "ready", "Ready"
        FAILED = "failed", "Needs attention"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fingerprint = models.CharField(max_length=64, unique=True, editable=False)
    title = models.CharField(max_length=160)
    source_url = models.URLField(max_length=2048)
    description = models.TextField(max_length=5000)
    kind = models.CharField(
        max_length=30, choices=Kind.choices, default=Kind.LANDING, db_index=True
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="designs")
    industry = models.CharField(max_length=60, blank=True, db_index=True)
    selector = models.CharField(max_length=200, blank=True)
    viewport_width = models.PositiveIntegerField(default=1440)
    screenshot = models.ImageField(upload_to="designs/screenshots/", blank=True)
    thumbnail = models.ImageField(upload_to="designs/thumbnails/", blank=True)
    capture_status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    capture_error = models.CharField(max_length=200, blank=True)
    design_markdown = models.TextField(blank=True)
    embedding = models.JSONField(default=list, blank=True)
    embedding_model = models.CharField(max_length=100, blank=True)
    embedding_error = models.CharField(max_length=200, blank=True)
    published = models.BooleanField(default=True, db_index=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    processing_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("design_detail", args=[self.pk])


class SavedDesign(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    design = models.ForeignKey(Design, on_delete=models.CASCADE, related_name="saves")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "design"], name="unique_saved_design")
        ]

    def __str__(self):
        return f"{self.user_id}: {self.design_id}"
