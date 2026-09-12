from django.db import models


class ProfileStates(models.TextChoices):
    STRANGER = "stranger"
    SIGNED_UP = "signed_up"
    # Freemium state set after the core activation action is completed.
    FREE = "free"

    ACCOUNT_DELETED = "account_deleted"


class EmailType(models.TextChoices):
    EMAIL_CONFIRMATION = "EMAIL_CONFIRMATION", "Email Confirmation"
    WELCOME = "WELCOME", "Welcome"
