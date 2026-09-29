from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.core.models import Profile


class Command(BaseCommand):
    help = "Idempotently provision encrypted API keys; preserve existing legacy credentials."

    def handle(self, *args, **options):
        count = 0
        for user in User.objects.iterator():
            profile, _ = Profile.objects.get_or_create(user=user)
            if not profile.api_key_encrypted:
                profile.ensure_api_key()
                count += 1
        self.stdout.write(f"Provisioned {count} accounts; no key values displayed.")
