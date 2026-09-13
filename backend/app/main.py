import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import ai, applications, auth, companies, drives, knowledge, students, tnpc
from app.core.config import settings
from app.core.observability import metrics, new_request_id, setup_logging

setup_logging()
logger = logging.getLogger("api")

# Warn (don't exit) on weak secrets here — MCP servers enforce strictly; the
# API keeps a single warning so local dev/tests are not blocked.
for problem in settings.validate_secrets():
    logger.warning("CONFIG: %s", problem)

app = FastAPI(title=settings.PROJECT_NAME)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attach a request id to every call and time it; never break the request."""
    rid = new_request_id()
    with metrics.timed("http_request"):
        response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    logger.info(
        "%s %s -> %s",
        request.method,
        request.url.path,
        response.status_code,
        extra={"request_id": rid, "status": response.status_code},
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    rid = getattr(request.state, "request_id", None) or new_request_id()
    logger.exception("unhandled error", extra={"request_id": rid})
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error", "request_id": rid},
    )


app.include_router(auth.router)
app.include_router(students.router)
app.include_router(drives.router)
app.include_router(companies.router)
app.include_router(applications.router)
app.include_router(ai.router)
app.include_router(knowledge.router)
app.include_router(tnpc.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "metrics": metrics.snapshot()}
