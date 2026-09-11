# Pydantic request/response schemas for the HTTP API.

import uuid

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    role: str
    full_name: str


class ProfileIn(BaseModel):
    roll_number: str = Field(min_length=1, max_length=40)
    branch: str = Field(min_length=1, max_length=60)
    graduation_year: int = Field(ge=2000, le=2100)
    cgpa: float | None = Field(default=None, ge=0, le=10)
    active_backlogs: int = Field(default=0, ge=0, le=20)
    skills: list[str] = Field(default_factory=list, max_length=30)


class ProfileOut(ProfileIn):
    user_id: uuid.UUID
    full_name: str
    email: str


class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str
    industry: str | None = None


class DriveOut(BaseModel):
    id: uuid.UUID
    title: str
    company: str
    company_id: uuid.UUID
    role: str
    ctc_lpa: float | None = None
    stipend_monthly: float | None = None
    location: str
    application_deadline: str
    status: str
    skills: list[str] = Field(default_factory=list)
    rules: dict | None = None


class DriveCreate(BaseModel):
    company_id: uuid.UUID
    title: str = Field(min_length=3, max_length=200)
    role: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=1, max_length=120)
    application_deadline: str = Field(min_length=8, max_length=32)
    ctc_lpa: float | None = Field(default=None, ge=0, le=1000)
    stipend_monthly: float | None = Field(default=None, ge=0)
    skills: list[str] = Field(default_factory=list, max_length=30)
    rules: dict = Field(default_factory=dict)


class EligibilityOut(BaseModel):
    drive_id: uuid.UUID
    drive_title: str
    eligible: bool
    reasons: list[str]
    missing_requirements: list[str]


class ApplicationCreate(BaseModel):
    drive_id: uuid.UUID
    idempotency_key: str | None = Field(default=None, max_length=64)


class ApplicationOut(BaseModel):
    id: uuid.UUID
    drive_id: uuid.UUID
    drive_title: str
    student_id: uuid.UUID
    status: str
    created_at: str


class ApplicationStatusUpdate(BaseModel):
    status: str = Field(min_length=3, max_length=20)
    reason: str | None = Field(default=None, max_length=500)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    thread_id: str | None = Field(default=None, max_length=80)


class ChatResponseOut(BaseModel):
    reply: str
    intent: str | None = None
    thread_id: str
    tools: list[str] = Field(default_factory=list)