# Created by Ryan Polasky | 8/30/25
# Lode | All Rights Reserved

from opensearchpy import OpenSearch

client = None


def get_opensearch_client():
    """Returns the OpenSearch client instance."""
    global client
    if client is None:
        client = OpenSearch(
            hosts=[{"host": "opensearch-node1", "port": 9200}],
            # todo - make this env var maybe? or research better way tbh
            use_ssl=False,  # for local dev only, use True in production
        )
    return client
