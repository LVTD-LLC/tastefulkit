"""Compatibility sinks for capture/index jobs queued before prepared ingestion.

Keep these import paths during rollout so old broker packages finish harmlessly.
Agents now prepare all assets and embeddings before the admin POST.
"""


def process_design(pk, attempt=0):
    return None


def index_design(pk, attempt=0):
    return None
