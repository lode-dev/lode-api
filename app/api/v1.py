# Created by Ryan Polasky | 8/30/25
# Lode | All Rights Reserved

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, WebSocket, WebSocketDisconnect, Request, Query

from app.db import get_opensearch_client
from app.websockets import manager

LogEntry = Dict[str, Any]
router = APIRouter()


@router.websocket("/ws/tail")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.post("/logs")
async def post_logs(logs: List[LogEntry] = Body(...)):
    client = get_opensearch_client()
    for log in logs:
        try:
            await client.index(
                index="lode-logs",
                body=log,
            )
            await manager.broadcast(log)
        except Exception as e:
            print(f"Error indexing log: {e}")
    return {"status": "logs received", "count": len(logs)}


@router.get("/search")
async def search_logs(
        request: Request,
        sort: Optional[str] = None,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=500)
):
    client = get_opensearch_client()

    from_offset = (page - 1) * page_size

    must_filters = []
    query_params = request.query_params
    general_search_term = query_params.get('q')
    if general_search_term:
        must_filters.append(
            {"multi_match": {"query": general_search_term, "fields": ["message", "level", "metadata.*"]}})

    for key, value in query_params.items():
        if key in ['sort', 'q', 'page', 'page_size']:
            continue
        must_filters.append({"match": {key: value}})

    query_body = {"query": {"bool": {"must": must_filters}}}
    if not must_filters:
        query_body['query'] = {"match_all": {}}

    if sort:
        try:
            field, order = sort.split(':')
            if field and order in ['asc', 'desc']:
                query_body['sort'] = [{field: {"order": order}}]
        except ValueError:
            print(f"Invalid sort parameter: {sort}")

    try:
        response = await client.search(
            index="lode-logs",
            body=query_body,
            size=page_size,
            from_=from_offset
        )
        results = [hit['_source'] for hit in response['hits']['hits']]
        total_hits = response['hits']['total']['value']
        return {"results": results, "total": total_hits, "page": page, "page_size": page_size}
    except Exception as e:
        print(f"Error searching logs: {e}")
        return {"error": "Failed to search logs"}


@router.get("/aggregations/suggested_filters")
async def get_suggested_filters():
    """
    Runs an aggregation query to find the most common values for key fields.
    """
    client = get_opensearch_client()

    query_body = {
        "size": 0,
        "aggs": {
            "common_levels": {
                "terms": {
                    "field": "level.keyword",
                    "size": 5
                }
            },
            "common_user_ids": {
                "terms": {
                    "field": "metadata.user_id.keyword",
                    "size": 5
                }
            }
        }
    }

    try:
        response = await client.search(
            index="lode-logs",
            body=query_body
        )
        return response['aggregations']
    except Exception as e:
        print(f"Error getting aggregations: {e}")
        return {"error": "Failed to get aggregations"}
