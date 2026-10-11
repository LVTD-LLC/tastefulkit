import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.pages.indexnow import IndexNowError, submit


class Command(BaseCommand):
    help = "Notify IndexNow only of changes since a complete public content snapshot."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--previous", type=Path, help="Complete pre-deployment content snapshot"
        )

    def handle(self, *args, **options):
        try:
            previous = json.loads(options["previous"].read_text()) if options["previous"] else None
            result = submit(settings.SITE_URL, previous, dry_run=options["dry_run"])
        except (IndexNowError, ValueError, OSError) as error:
            raise CommandError(str(error)) from None
        self.stdout.write(result)
