import logging
from src.config import settings

logger = logging.getLogger(__name__)

_client = None
_container = None


def get_cosmos_container():
    """Return the Cosmos DB container client, or None if not configured."""
    global _client, _container
    if _container is not None:
        return _container

    if not settings.cosmos_endpoint:
        logger.info("Cosmos DB not configured; state persistence disabled.")
        return None

    try:
        from azure.cosmos import CosmosClient
        if settings.cosmos_key:
            _client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
        else:
            from azure.identity import DefaultAzureCredential
            _client = CosmosClient(settings.cosmos_endpoint, credential=DefaultAzureCredential())

        db = _client.get_database_client(settings.cosmos_database)
        _container = db.get_container_client("review-state")
        logger.info("Cosmos DB container initialized.")
        return _container
    except Exception as e:
        logger.warning("Failed to initialize Cosmos DB: %s", e)
        return None


def save_review_state(session_id: str, state: dict):
    """Persist a review state snapshot to Cosmos DB."""
    container = get_cosmos_container()
    if container is None:
        return
    item = {"id": session_id, "session_id": session_id, **state}
    container.upsert_item(item)


def load_review_state(session_id: str) -> dict | None:
    """Load a review state snapshot from Cosmos DB."""
    container = get_cosmos_container()
    if container is None:
        return None
    try:
        return container.read_item(item=session_id, partition_key=session_id)
    except Exception:
        return None
