from contextlib import nullcontext

import pytest
from qdrant_client import QdrantClient


@pytest.fixture
def qdrant_store(settings, monkeypatch):
    settings.QDRANT_URL = "http://qdrant.test:6333"
    settings.QDRANT_COLLECTION = "test-designs"
    client = QdrantClient(":memory:")
    monkeypatch.setattr("apps.catalogue.vector_store.get_client", lambda: nullcontext(client))
    monkeypatch.setattr(
        "apps.catalogue.management.commands.backfill_qdrant.get_client",
        lambda: nullcontext(client),
    )
    yield client
    client.close()
