import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import ai, applications, auth, companies, drives, students, tnpc
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Don't leak internals; log via structured logging in Phase 10
    return JSONResponse(status_code=500, content={"detail": "internal server error"})

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(drives.router)
app.include_router(companies.router)
app.include_router(applications.router)
app.include_router(ai.router)
app.include_router(tnpc.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}