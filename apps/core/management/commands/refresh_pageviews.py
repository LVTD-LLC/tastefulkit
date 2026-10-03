from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.traffic import refresh_pageviews


class Command(BaseCommand):
    help = "Refresh the public 24-hour pageview count or install its five-minute schedule."

    def add_arguments(self, parser):
        parser.add_argument("--schedule", action="store_true")

    def handle(self, *args, **options):
        if options["schedule"]:
            from django_q.models import Schedule

            Schedule.objects.get_or_create(
                name="navbar-pageviews",
                defaults={
                    "func": "apps.core.traffic.refresh_pageviews",
                    "schedule_type": Schedule.MINUTES,
                    "minutes": 5,
                    "next_run": timezone.now() + timedelta(minutes=1),
                },
            )
            self.stdout.write("Pageview refresh schedule ready.")
        else:
            self.stdout.write(
                "Updated." if refresh_pageviews() else "Unavailable; cache unchanged."
            )
