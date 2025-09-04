# Created by Ryan Polasky | 8/30/25
# Lode | All Rights Reserved

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, WebSocket, WebSocketDisconnect, Request, Query
import ollama
import json
import asyncio

from app.db import get_opensearch_client, get_context_logs_from_filters
from app.websockets import manager
from app.config import settings

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


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect(websocket)
    current_stream_task = None
    
    try:
        while True:
            message_text = await websocket.receive_text()
            
            # Check for interruption command
            if message_text == "INTERRUPT":
                if current_stream_task and not current_stream_task.done():
                    current_stream_task.cancel()
                    await websocket.send_text("\n\n[Stream interrupted by user]\n")
                continue
            
            # Cancel any existing stream before starting a new one
            if current_stream_task and not current_stream_task.done():
                current_stream_task.cancel()
            
            async def handle_message():
                try:
                    # Parse the structured JSON message
                    message_data = json.loads(message_text)
                    question = message_data.get("question", "")
                    context_logs = message_data.get("context_logs", [])
                    active_filters = message_data.get("active_filters", {})
                    
                    # Conditional context building
                    if context_logs:
                        # Use explicit context logs provided by user
                        relevant_logs = context_logs
                    else:
                        # Fall back to automatic context mode using active filters
                        relevant_logs = await get_context_logs_from_filters(active_filters)
                    
                    # Build context string from logs
                    context_str = ""
                    if relevant_logs:
                        context_str = "\n\nRelevant log entries:\n"
                        for i, log in enumerate(relevant_logs[:20], 1):  # Limit to top 20
                            log_summary = f"Log {i}:\n"
                            log_summary += f"  Timestamp: {log.get('timestamp', 'N/A')}\n"
                            log_summary += f"  Level: {log.get('level', 'N/A')}\n"
                            log_summary += f"  Message: {log.get('message', 'N/A')}\n"
                            if log.get('metadata'):
                                log_summary += f"  Metadata: {log.get('metadata')}\n"
                            context_str += log_summary + "\n"

                    prompt = f"""
                    You are an expert debugging assistant named Lode.
                    A user has the following question about their application logs: "{question}"
                    {context_str}
                    Based on the provided log context, provide a helpful, concise answer that references specific logs when relevant.
                    If no relevant logs are provided, give general debugging guidance.
                    """

                    ollama_client = ollama.AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")

                    stream = await ollama_client.chat(
                        model=settings.OLLAMA_MODEL,
                        messages=[{'role': 'user', 'content': prompt}],
                        stream=True
                    )

                    async for chunk in stream:
                        token = chunk['message']['content']
                        await websocket.send_text(token)
                        
                except json.JSONDecodeError:
                    # Handle legacy plain text messages for backward compatibility
                    question = message_text
                    prompt = f"""
                    You are an expert debugging assistant named Lode.
                    A user has the following question about their application logs: "{question}"
                    Provide a helpful, concise answer.
                    """

                    ollama_client = ollama.AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")

                    stream = await ollama_client.chat(
                        model=settings.OLLAMA_MODEL,
                        messages=[{'role': 'user', 'content': prompt}],
                        stream=True
                    )

                    async for chunk in stream:
                        token = chunk['message']['content']
                        await websocket.send_text(token)
                except asyncio.CancelledError:
                    # Stream was cancelled, exit gracefully
                    raise
                except Exception as e:
                    await websocket.send_text(f"\n\n[Error: {str(e)}]\n")
            
            # Start the message handling as a task that can be cancelled
            current_stream_task = asyncio.create_task(handle_message())
            
            try:
                await current_stream_task
            except asyncio.CancelledError:
                # Task was cancelled, continue to next message
                pass

    except WebSocketDisconnect:
        if current_stream_task and not current_stream_task.done():
            current_stream_task.cancel()
        manager.disconnect(websocket)
