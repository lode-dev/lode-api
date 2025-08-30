# Created by Ryan Polasky | 8/30/25
# Lode | All Rights Reserved

import uvicorn
from fastapi import FastAPI
from app.api import v1

app = FastAPI(
    title="Lode API",
    version="0.1.0",
    description="The ingestion and query API for the Lode log analysis platform.",
)


@app.get("/")
def read_root():
    """A simple health check endpoint to confirm the API is running."""
    return {"status": "ok"}


app.include_router(v1.router, prefix="/v1", tags=["v1"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
