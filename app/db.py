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


async def get_context_logs_from_filters(active_filters: dict, limit: int = 15):
    """
    Retrieves relevant logs based on active filters for automatic context building.
    """
    client = get_opensearch_client()
    
    must_filters = []
    
    # Build query from active filters
    for key, value in active_filters.items():
        if key == 'q':  # General search term
            must_filters.append(
                {"multi_match": {"query": value, "fields": ["message", "level", "metadata.*"]}}
            )
        else:
            must_filters.append({"match": {key: value}})
    
    query_body = {
        "query": {"bool": {"must": must_filters}} if must_filters else {"match_all": {}},
        "sort": [{"@timestamp": {"order": "desc"}}],  # Most recent first
        "size": limit
    }
    
    try:
        response = await client.search(
            index="lode-logs",
            body=query_body
        )
        return [hit['_source'] for hit in response['hits']['hits']]
    except Exception as e:
        print(f"Error retrieving context logs: {e}")
        return []
