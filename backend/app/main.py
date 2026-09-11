from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai, applications, auth, companies, drives, students
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(drives.router)
app.include_router(companies.router)
app.include_router(applications.router)
app.include_router(ai.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}