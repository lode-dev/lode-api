# Created by Ryan Polasky | 8/30/25
# Lode | All Rights Reserved

from opensearchpy import AsyncOpenSearch

client = None


def get_opensearch_client():
    """Returns the AsyncOpenSearch client instance."""
    global client
    if client is None:
        client = AsyncOpenSearch(
            hosts=[{"host": "opensearch-node1", "port": 9200}],
            use_ssl=False,
        )
    return client