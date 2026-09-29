from django.contrib.auth.models import User
from django.db import models, transaction
from django_q.tasks import async_task

from apps.core.base_models import BaseModel
from apps.core.choices import EmailType, ProfileStates
from apps.core.model_utils import (
    decrypt_api_key,
    encrypt_api_key,
    generate_api_key,
    get_api_key_prefix,
    hash_api_key,
    verify_api_key,
)


class Profile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    api_key_prefix = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        default=None,
    )
    api_key_hash = models.CharField(max_length=128, blank=True, default="")

    api_key_encrypted = models.TextField(blank=True, default="", editable=False)
    legacy_api_key_prefix = models.CharField(
        max_length=32, unique=True, null=True, blank=True, default=None, editable=False
    )
    legacy_api_key_hash = models.CharField(max_length=128, blank=True, default="", editable=False)

    state = models.CharField(
        max_length=255,
        choices=ProfileStates.choices,
        default=ProfileStates.STRANGER,
        help_text="The current state of the user's profile",
    )

    def track_state_change(self, to_state, metadata=None, source_function=None):
        async_task(
            "apps.core.tasks.track_state_change",
            profile_id=self.id,
            from_state=self.current_state,
            to_state=to_state,
            metadata=metadata,
            source_function=source_function,
            group="Track State Change",
        )

    @property
    def current_state(self):
        if not self.state_transitions.all().exists():
            return ProfileStates.STRANGER
        latest_transition = self.state_transitions.latest("created_at")
        return latest_transition.to_state

    @property
    def has_api_key(self):
        return bool(self.api_key_hash and self.api_key_prefix)

    def set_api_key(self, api_key=None):
        api_key = api_key or generate_api_key()
        api_key_prefix = get_api_key_prefix(api_key)
        if not api_key_prefix:
            raise ValueError("API keys must include a public prefix and secret.")

        self.api_key_prefix = api_key_prefix
        self.api_key_hash = hash_api_key(api_key)
        self.api_key_encrypted = encrypt_api_key(api_key)
        return api_key

    def ensure_api_key(self):
        """Provision once under lock, preserving an unrecoverable legacy credential."""
        with transaction.atomic():
            current = Profile.objects.select_for_update().get(pk=self.pk)
            if current.api_key_encrypted:
                key = decrypt_api_key(current.api_key_encrypted)
            else:
                if current.has_api_key:
                    current.legacy_api_key_prefix = current.api_key_prefix
                    current.legacy_api_key_hash = current.api_key_hash
                key = current.set_api_key()
                current.save(update_fields=self._key_fields())
            self._copy_key_fields(current)
            return key

    @staticmethod
    def _key_fields():
        return [
            "api_key_prefix",
            "api_key_hash",
            "api_key_encrypted",
            "legacy_api_key_prefix",
            "legacy_api_key_hash",
            "updated_at",
        ]

    def _copy_key_fields(self, other):
        for field in self._key_fields():
            setattr(self, field, getattr(other, field))

    def rotate_api_key(self):
        with transaction.atomic():
            current = Profile.objects.select_for_update().get(pk=self.pk)
            api_key = current.set_api_key()
            current.legacy_api_key_prefix = None
            current.legacy_api_key_hash = ""
            current.save(update_fields=self._key_fields())
            self._copy_key_fields(current)
            return api_key

    def check_api_key(self, api_key):
        prefix = get_api_key_prefix(api_key)
        if not prefix:
            return False
        if prefix == self.api_key_prefix:
            return verify_api_key(api_key, self.api_key_hash)
        if prefix == self.legacy_api_key_prefix:
            return verify_api_key(api_key, self.legacy_api_key_hash)
        return False


class ProfileStateTransition(BaseModel):
    profile = models.ForeignKey(
        Profile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="state_transitions",
    )
    from_state = models.CharField(max_length=255, choices=ProfileStates.choices)
    to_state = models.CharField(max_length=255, choices=ProfileStates.choices)
    backup_profile_id = models.IntegerField()
    metadata = models.JSONField(null=True, blank=True)


class EmailSent(BaseModel):
    email_address = models.EmailField(help_text="The recipient email address")
    email_type = models.CharField(
        max_length=50, choices=EmailType.choices, help_text="Type of email sent"
    )
    profile = models.ForeignKey(
        Profile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="emails_sent",
        help_text="Associated user profile, if applicable",
    )

    class Meta:
        verbose_name = "Email Sent"
        verbose_name_plural = "Emails Sent"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email_type} to {self.email_address}"
