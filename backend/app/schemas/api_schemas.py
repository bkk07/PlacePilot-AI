# Pydantic request/response schemas for the HTTP API.

import uuid
from datetime import datetime

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
    # student information
    personal_email: str | None = Field(default=None, max_length=120)
    phone_number: str | None = Field(default=None, max_length=20)
    # B.Tech academic
    degree: str = Field(default="B.Tech", max_length=40)
    specialization: str | None = Field(default=None, max_length=80)
    admission_year: int | None = Field(default=None, ge=1990, le=2100)
    current_year: int | None = Field(default=None, ge=1, le=6)
    current_semester: int | None = Field(default=None, ge=1, le=12)
    # school academic details
    tenth_percentage: float | None = Field(default=None, ge=0, le=100)
    tenth_board: str | None = Field(default=None, max_length=80)
    twelfth_percentage: float | None = Field(default=None, ge=0, le=100)
    twelfth_board: str | None = Field(default=None, max_length=80)
    diploma_percentage: float | None = Field(default=None, ge=0, le=100)
    # backlog / eligibility
    history_of_backlogs: int = Field(default=0, ge=0, le=20)
    year_gaps: int = Field(default=0, ge=0, le=10)


class ProfileOut(ProfileIn):
    user_id: uuid.UUID
    full_name: str
    email: str
    profile_photo_id: uuid.UUID | None = None


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    legal_name: str | None = None
    website: str | None = None
    industry: str | None = None
    company_size: str | None = None
    description: str | None = None
    headquarters: str | None = None


class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str
    legal_name: str | None = None
    website: str | None = None
    industry: str | None = None
    company_size: str | None = None
    description: str | None = None
    headquarters: str | None = None


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
    description: str | None = None
    drive_type: str | None = None
    mode: str | None = None
    registration_start: str | None = None
    registration_end: str | None = None
    venue: str | None = None
    meeting_link: str | None = None


class DriveCreate(BaseModel):
    company_id: uuid.UUID
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    drive_type: str = Field(default="ON_CAMPUS", max_length=20)
    mode: str = Field(default="OFFLINE", max_length=20)
    registration_start: datetime | None = None
    registration_end: datetime | None = None
    drive_start_date: datetime | None = None
    drive_end_date: datetime | None = None
    venue: str | None = None
    meeting_link: str | None = None
    application_limit: int | None = Field(default=None, ge=1)
    instructions: str | None = None
    role: str = Field(default="Software Engineer", min_length=2, max_length=120)
    location: str = Field(default="Bangalore", min_length=1, max_length=120)
    application_deadline: str = Field(default="2026-12-31", min_length=8, max_length=32)
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