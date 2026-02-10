import logging

from mcp_server_qdrant.qdrant.config import EmbeddingProviderSettings
from mcp_server_qdrant.qdrant.embeddings.base import EmbeddingProvider
from mcp_server_qdrant.qdrant.embeddings.types import EmbeddingProviderType

# Get module-level logger
logger = logging.getLogger(__name__)


def create_embedding_provider(settings: EmbeddingProviderSettings) -> EmbeddingProvider:
    """
    Create an embedding provider based on the specified type.
    :param settings: The settings for the embedding provider.
    :return: An instance of the specified embedding provider.
    """
    logger.info(
        f"Creating embedding provider of type {settings.provider_type} with model {settings.model_name}"
    )

    if settings.provider_type == EmbeddingProviderType.FASTEMBED:
        from mcp_server_qdrant.qdrant.embeddings.fastembed import FastEmbedProvider

        return FastEmbedProvider(settings.model_name)

    logger.error(f"Unsupported embedding provider: {settings.provider_type}")
    raise ValueError(f"Unsupported embedding provider: {settings.provider_type}")
