# Created by Ryan Polasky | 8/30/25
# Lode | All Rights Reserved

from typing import Any, Dict, List
from fastapi import APIRouter, Body

LogEntry = Dict[str, Any]

router = APIRouter()


@router.post("/logs")
def post_logs(logs: List[LogEntry] = Body(...)):
    """
    Ingestion endpoint for receiving log entries. For now, it just prints the logs to the console.
    """
    print(f"Received {len(logs)} log(s).")
    for log in logs:
        print(log)

    return {"status": "logs received", "count": len(logs)}