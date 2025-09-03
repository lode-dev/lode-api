# Created by Ryan Polasky | 8/30/25
# Lode | All Rights Reserved

from opensearchpy import AsyncOpenSearch
from app.config import settings

client = None


def get_opensearch_client():
    """Returns the AsyncOpenSearch client instance."""
    global client
    if client is None:
        client = AsyncOpenSearch(
            hosts=[{"host": settings.OPENSEARCH_HOST, "port": settings.OPENSEARCH_PORT}],
            use_ssl=settings.OPENSEARCH_SSL,
        )
    return client
