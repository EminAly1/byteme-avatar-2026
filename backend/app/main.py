import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.prediction_api import router as prediction_router
from app.alert_api import router as alert_router
from app.document_api import router as document_router
from app.errors import DomainError
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import check_database

logger = logging.getLogger(__name__)
app = FastAPI(title="AVATAR API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Idempotency-Key", "X-API-Key"],
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


@app.exception_handler(DomainError)
async def domain_error(request, exc):
    return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}})


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    logger.warning("Database operation failed; credentials and statements omitted")
    return JSONResponse(status_code=503, content={"error": {"code": "DATABASE_UNAVAILABLE", "message": "Veritabanı işlemi gerçekleştirilemedi", "details": {}}})


app.include_router(router)
app.include_router(prediction_router)
app.include_router(alert_router)
app.include_router(document_router)
