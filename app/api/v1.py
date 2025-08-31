# Created by Ryan Polasky | 8/30/25
# Lode | All Rights Reserved

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, WebSocket, WebSocketDisconnect

from app.db import get_opensearch_client
from app.websockets import manager

LogEntry = Dict[str, Any]

router = APIRouter()


@router.post("/logs")
async def post_logs(logs: List[LogEntry] = Body(...)):
    client = get_opensearch_client()

    for log in logs:
        try:
            client.index(
                index="lode-logs",
                body=log,
            )
            await manager.broadcast(log)
        except Exception as e:
            print(f"Error indexing log: {e}")

    return {"status": "logs received", "count": len(logs)}


@router.get("/search")
async def search_logs(q: Optional[str] = None):
    """
    Search endpoint for querying log entries from OpenSearch.
    """
    client = get_opensearch_client()

    if q:
        query = {
            "query": {
                "multi_match": {
                    "query": q,
                    "fields": ["message", "level", "metadata.*"]
                }
            }
        }
    else:
        query = {
            "query": {
                "match_all": {}
            }
        }

    try:
        response = client.search(
            index="lode-logs",
            body=query
        )
        results = [hit['_source'] for hit in response['hits']['hits']]
        return {"results": results}
    except Exception as e:
        print(f"Error searching logs: {e}")
        return {"error": "Failed to search logs"}


@router.websocket("/ws/tail")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
