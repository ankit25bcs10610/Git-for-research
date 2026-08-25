import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_collab, routes_crdt, routes_ingestion, routes_retrieval, routes_users, routes_versioning

app = FastAPI(title="Git for Research API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_ingestion.router, prefix="/api", tags=["ingestion"])
app.include_router(routes_versioning.router, prefix="/api", tags=["versioning"])
app.include_router(routes_collab.router, prefix="/api", tags=["collaboration"])
app.include_router(routes_retrieval.router, prefix="/api", tags=["retrieval"])
app.include_router(routes_users.router, prefix="/api", tags=["users"])
app.include_router(routes_crdt.router, prefix="/api", tags=["crdt"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
