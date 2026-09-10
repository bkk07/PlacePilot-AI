# Pydantic input schemas for every MCP tool — validation happens before execution.

from pydantic import BaseModel, Field


class SearchDrivesInput(BaseModel):
    query: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=120)
    role: str = Field(default="", max_length=120)


class DriveIdInput(BaseModel):
    drive_id: str = Field(min_length=1, max_length=64)


class StudentIdInput(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)


class CheckEligibilityInput(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)
    drive_id: str = Field(default="", max_length=64)
    drive: str = Field(default="", max_length=200)


class PolicyQueryInput(BaseModel):
    query: str = Field(min_length=3, max_length=500)


class RecommendationsInput(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)


class CreateDriveInput(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    company_id: str = Field(min_length=1, max_length=64)
    role: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=1, max_length=120)
    application_deadline: str = Field(min_length=1, max_length=32)
    ctc_lpa: float | None = Field(default=None, ge=0, le=1000)
    stipend_monthly: float | None = Field(default=None, ge=0)
    skills: list[str] = Field(default_factory=list, max_length=20)
    rules: dict = Field(default_factory=dict)


class UpdateApplicationStatusInput(BaseModel):
    application_id: str = Field(min_length=1, max_length=64)
    new_status: str = Field(min_length=1, max_length=32)
    reason: str = Field(default="", max_length=500)
