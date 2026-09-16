from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalogue.models import Design
from apps.catalogue.providers import EMBEDDING_MODEL
from apps.catalogue.vector_store import (
    ensure_collection,
    get_client,
    upsert_vector,
    validate_vector,
)


class Command(BaseCommand):
    help = "Import existing legacy vectors only; missing vectors must be prepared by an agent."

    def handle(self, *args, **options):
        try:
            with get_client() as client:
                ensure_collection(client)
        except Exception as exc:
            raise CommandError(f"Qdrant collection unavailable ({type(exc).__name__}).") from None
        indexed = failed = skipped = 0
        for design in Design.objects.filter(capture_status=Design.Status.READY).iterator(
            chunk_size=100
        ):
            try:
                with get_client() as client:
                    existing = client.retrieve(
                        settings.QDRANT_COLLECTION, ids=[str(design.pk)], with_payload=True
                    )
                if (
                    existing
                    and (existing[0].payload or {}).get("embedding_model") == EMBEDDING_MODEL
                ):
                    skipped += 1
                    continue
                vector = design.embedding
                validate_vector(vector)
                if design.embedding_model != EMBEDDING_MODEL:
                    raise ValueError("Resubmit a prepared vector using the current model.")
                upsert_vector(design.pk, vector)
                Design.objects.filter(pk=design.pk).update(
                    embedding_model=EMBEDDING_MODEL, embedding_error=""
                )
                indexed += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(f"Index failed for {design.pk} ({type(exc).__name__}).")
        self.stdout.write(f"Indexed: {indexed}; existing: {skipped}; failed: {failed}.")
        if failed:
            raise CommandError(
                "Backfill incomplete; resubmit complete prepared examples through the admin POST."
            )
