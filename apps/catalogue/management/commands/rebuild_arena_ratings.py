from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalogue.arena import lock_arena, update_global
from apps.catalogue.models import ArenaBallot, DesignRating


class Command(BaseCommand):
    help = "Rebuild global Elo from the immutable counted ballot history, in ballot order."

    @transaction.atomic
    def handle(self, *args, **options):
        lock_arena()
        DesignRating.objects.all().delete()
        ballots = ArenaBallot.objects.filter(global_counted=True).order_by("id")
        count = 0
        for ballot in ballots.iterator():
            update_global(ballot)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Replayed {count} global ballots."))
