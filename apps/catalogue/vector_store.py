"""Qdrant owns live vectors; PostgreSQL remains the filter/visibility authority."""

import math
from itertools import batched
from uuid import UUID

from django.conf import settings
from qdrant_client import QdrantClient, models

from apps.catalogue.providers import EMBEDDING_MODEL

DIMENSIONS = 768


def get_client():
    if not settings.QDRANT_URL:
        raise ValueError("Qdrant is not configured.")
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        timeout=settings.QDRANT_TIMEOUT_SECONDS,
        check_compatibility=False,
    )


def validate_vector(vector):
    if (
        len(vector) != DIMENSIONS
        or any(not math.isfinite(float(value)) for value in vector)
        or not any(vector)
    ):
        raise ValueError("Expected a finite, nonzero 768-dimensional embedding.")


def ensure_collection(client):
    collection = settings.QDRANT_COLLECTION
    if not client.collection_exists(collection):
        try:
            client.create_collection(
                collection,
                vectors_config=models.VectorParams(
                    size=DIMENSIONS, distance=models.Distance.COSINE
                ),
            )
        except Exception:
            # Another worker may have won collection creation. Validate its contract.
            if not client.collection_exists(collection):
                raise
    validate_collection(client)


def validate_collection(client):
    vectors = client.get_collection(settings.QDRANT_COLLECTION).config.params.vectors
    if not isinstance(vectors, models.VectorParams) or (
        vectors.size != DIMENSIONS or vectors.distance != models.Distance.COSINE
    ):
        raise ValueError("Qdrant collection has an incompatible vector contract.")


def upsert_vector(pk, vector):
    validate_vector(vector)
    with get_client() as client:
        ensure_collection(client)
        client.upsert(
            settings.QDRANT_COLLECTION,
            points=[
                models.PointStruct(
                    id=str(pk), vector=vector, payload={"embedding_model": EMBEDDING_MODEL}
                )
            ],
            wait=True,
        )


def search_vectors(designs, vector):
    """Filter before ranking, including saves; never transfer stored vectors to Django.

    Batch authoritative IDs rather than mirror mutable metadata/permissions in Qdrant.
    All eligible batches are searched, so excluded points cannot starve matches.
    """
    validate_vector(vector)
    ranked = []
    with get_client() as client:
        validate_collection(client)
        ids = designs.order_by("pk").values_list("pk", flat=True).iterator(chunk_size=256)
        for batch in batched(ids, 256, strict=False):
            result = client.query_points(
                settings.QDRANT_COLLECTION,
                query=vector,
                query_filter=models.Filter(
                    must=[
                        models.HasIdCondition(has_id=[str(pk) for pk in batch]),
                        models.FieldCondition(
                            key="embedding_model", match=models.MatchValue(value=EMBEDDING_MODEL)
                        ),
                    ]
                ),
                score_threshold=0.45,
                limit=len(batch),
                with_payload=False,
                with_vectors=False,
            )
            ranked.extend((UUID(str(point.id)), point.score) for point in result.points)
    return sorted(ranked, key=lambda item: (-item[1], str(item[0])))


def collection_healthy():
    try:
        with get_client() as client:
            validate_collection(client)
        return True
    except Exception:
        return False
