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


class ArenaState(models.Model):
    """Singleton lock: ballot order and Elo updates share one transaction."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)

    def __str__(self):
        return "Arena write lock"


class TasteProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    generation = models.PositiveIntegerField(default=0)
    reset_at = models.DateTimeField(null=True, blank=True)
    rate_window = models.DateTimeField(null=True, blank=True)
    rate_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Taste profile {self.user_id}"


class ArenaGuest(models.Model):
    """Opaque browser-session identity; no account or personal taste profile."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rate_window = models.DateTimeField(null=True, blank=True)
    rate_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return "Arena guest"


class ArenaBallot(models.Model):
    # UUID snapshots retain replay after catalogue deletion; no source/user content.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    guest = models.ForeignKey(ArenaGuest, null=True, on_delete=models.SET_NULL)
    generation = models.PositiveIntegerField(default=0)
    design_a = models.UUIDField()
    design_b = models.UUIDField()
    winner = models.UUIDField()
    global_counted = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(user__isnull=True) | models.Q(guest__isnull=True),
                name="arena_single_voter_type",
            ),
            models.UniqueConstraint(
                fields=["guest", "design_a", "design_b"], name="arena_one_guest_pair"
            ),
            models.CheckConstraint(
                condition=models.Q(design_a__lt=models.F("design_b")), name="arena_ordered_pair"
            ),
            models.CheckConstraint(
                condition=models.Q(winner=models.F("design_a"))
                | models.Q(winner=models.F("design_b")),
                name="arena_winner_in_pair",
            ),
            models.UniqueConstraint(
                fields=["user", "generation", "design_a", "design_b"],
                name="arena_one_personal_pair",
            ),
            models.UniqueConstraint(
                fields=["user", "design_a", "design_b"],
                condition=models.Q(global_counted=True),
                name="arena_one_global_pair",
            ),
        ]
        indexes = [models.Index(fields=["user", "generation"], name="arena_personal_history")]

    def __str__(self):
        return f"Arena ballot {self.pk}"


class DesignRating(models.Model):
    # Historical opponents remain replayable when references are deleted.
    design_id = models.UUIDField(primary_key=True)
    score = models.FloatField(default=1000)
    comparisons = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Rating {self.design_id}"
