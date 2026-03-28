import logging
from src.config import settings

logger = logging.getLogger(__name__)

_client = None


def get_keyvault_client():
    """Return the Key Vault SecretClient, or None if not configured."""
    global _client
    if _client is not None:
        return _client

    if not settings.keyvault_url:
        logger.info("Key Vault not configured; using environment variables for secrets.")
        return None

    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        _client = SecretClient(vault_url=settings.keyvault_url, credential=DefaultAzureCredential())
        logger.info("Key Vault client initialized.")
        return _client
    except Exception as e:
        logger.warning("Failed to initialize Key Vault client: %s", e)
        return None


def get_secret(name: str) -> str | None:
    """Retrieve a secret value from Key Vault."""
    client = get_keyvault_client()
    if client is None:
        return None
    try:
        return client.get_secret(name).value
    except Exception as e:
        logger.warning("Failed to retrieve secret '%s': %s", name, e)
        return None
