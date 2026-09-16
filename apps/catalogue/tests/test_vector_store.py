from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from qdrant_client import models

from apps.catalogue.models import Design, SavedDesign, Tag
from apps.catalogue.providers import EMBEDDING_MODEL
from apps.catalogue.services import search_designs
from apps.catalogue.vector_store import collection_healthy, ensure_collection, upsert_vector

pytestmark = pytest.mark.django_db
VECTOR = [1.0] + [0.0] * 767


def make_design(user, **kwargs):
    return Design.objects.create(
        submitted_by=user,
        title="Literal title",
        description="Warm layout",
        fingerprint=str(Design.objects.count()),
        capture_status="ready",
        **kwargs,
    )


def test_authoritative_filters_hide_stale_points(user, qdrant_store):
    design = make_design(user, kind="hero", industry="Software")
    design.tags.add(Tag.objects.create(name="minimal"))
    upsert_vector(design.pk, VECTOR)
    with patch("apps.catalogue.services.embed", return_value=VECTOR):
        assert search_designs("cozy", kind="hero", tag="minimal", industry="software")[0] == [
            design
        ]
        assert search_designs("cozy", kind="pricing_page")[0] == []
        assert search_designs("cozy", tag="editorial")[0] == []
        assert search_designs("cozy", industry="finance")[0] == []
        other = User.objects.create_user(username="other")
        SavedDesign.objects.create(user=other, design=design)
        assert search_designs("cozy", saved_by=user)[0] == []
        SavedDesign.objects.create(user=user, design=design)
        assert search_designs("cozy", saved_by=user)[0] == [design]
        Design.objects.filter(pk=design.pk).update(published=False)
        assert search_designs("cozy")[0] == []
        Design.objects.filter(pk=design.pk).update(published=True, capture_status="failed")
        assert search_designs("cozy")[0] == []
        design.delete()
        assert search_designs("cozy")[0] == []


def test_semantic_ranking_threshold_dedup_and_no_postgres_vectors(user, qdrant_store):
    literal = make_design(user)
    near = make_design(user)
    far = make_design(user)
    near.title = "Related reference"
    near.save()
    far.title = "Unrelated reference"
    far.save()
    upsert_vector(literal.pk, VECTOR)
    upsert_vector(near.pk, [0.8, 0.6] + [0.0] * 766)
    upsert_vector(far.pk, [-1.0] + [0.0] * 767)
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with (
        patch("apps.catalogue.services.embed", return_value=VECTOR),
        CaptureQueriesContext(connection) as queries,
    ):
        result, mode = search_designs("Literal")
    assert mode == "semantic" and result == [literal, near]
    assert all('"embedding"' not in q["sql"] for q in queries)


def test_qdrant_outage_and_bad_query_fall_back_to_text(user, qdrant_store):
    design = make_design(user)
    with patch("apps.catalogue.services.embed", return_value=VECTOR):
        result, mode = search_designs("Literal")  # missing collection
    assert mode == "text" and list(result) == [design]
    with patch("apps.catalogue.services.embed", return_value=[float("nan")] * 768):
        assert search_designs("Literal")[1] == "text"


def test_backfill_reuses_legacy_vectors_and_is_idempotent(user, qdrant_store):
    design = make_design(user, embedding=VECTOR, embedding_model=EMBEDDING_MODEL)
    for _ in range(2):
        call_command("backfill_qdrant", stdout=StringIO())
    assert qdrant_store.get_collection("test-designs").points_count == 1
    assert qdrant_store.retrieve("test-designs", ids=[str(design.pk)])[0].id == str(design.pk)
    design.refresh_from_db()
    assert design.embedding == VECTOR  # rollback archive, never read by search


def test_collection_contract_fails_closed(qdrant_store):
    qdrant_store.create_collection(
        "test-designs", vectors_config=models.VectorParams(size=3, distance=models.Distance.DOT)
    )
    with pytest.raises(ValueError, match="incompatible"):
        ensure_collection(qdrant_store)
    assert not collection_healthy()


def test_health_reports_qdrant_outage(client, qdrant_store):
    response = client.get("/api/healthcheck")
    assert response.status_code == 503 and response.json()["checks"]["qdrant"] is False
    ensure_collection(qdrant_store)
    response = client.get("/api/healthcheck")
    assert response.status_code == 200 and response.json()["checks"]["qdrant"] is True


def test_all_eligible_batches_are_searched(user, qdrant_store):
    from uuid import UUID

    designs = [
        Design(
            id=UUID(int=i + 1),
            submitted_by=user,
            fingerprint=f"batch-{i}",
            title="Reference",
            description="Layout",
            capture_status="ready",
        )
        for i in range(257)
    ]
    Design.objects.bulk_create(designs)
    # The only match is beyond the first allowed-ID batch.
    upsert_vector(designs[-1].pk, VECTOR)
    with patch("apps.catalogue.services.embed", return_value=VECTOR):
        assert search_designs("cozy")[0] == [designs[-1]]


def test_client_factory_closes_real_sdk_client(settings, monkeypatch):
    from qdrant_client import QdrantClient

    from apps.catalogue.vector_store import get_client

    settings.QDRANT_URL = "http://qdrant.test:6333"
    client = QdrantClient(":memory:")
    monkeypatch.setattr("apps.catalogue.vector_store.QdrantClient", lambda **kwargs: client)
    with get_client() as opened:
        assert opened.get_collections().collections == []
    with pytest.raises(RuntimeError, match="closed"):
        client.get_collections()
