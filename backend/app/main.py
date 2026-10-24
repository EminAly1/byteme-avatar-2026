import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import check_database

logger = logging.getLogger(__name__)
app = FastAPI(title="AVATAR API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()],
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    """Process liveness only; readiness is a separate database check."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["operations"])
def readiness() -> dict[str, str]:
    try:
        check_database()
    except (SQLAlchemyError, ValueError):
        # Do not expose database connection strings or credentials in API responses/logs.
        logger.warning("Database readiness check failed; check MySQL service and MYSQL_* settings")
        raise HTTPException(status_code=503, detail="Database unavailable or not configured") from None
    return {"status": "ok", "database": "ok"}
