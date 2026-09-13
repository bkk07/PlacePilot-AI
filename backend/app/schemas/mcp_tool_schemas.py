# Pydantic input schemas for every MCP tool — validation happens before execution.

from pydantic import BaseModel, Field, field_validator


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
    company: str = Field(default="", max_length=120, description="Optional company filter (e.g. 'TCS', 'Nimbus')")
    document_type: str = Field(default="", max_length=60, description="Optional type filter: job_description, interview_experience, placement_policy, eligibility_matrix, ...")
    top_k: int = Field(default=3, ge=1, le=10)


class RecommendationsInput(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)


def _validate_deadline(value: str) -> str:
    from datetime import date

    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("application_deadline must be an ISO date (YYYY-MM-DD)") from exc
    return value


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

    @field_validator("application_deadline")
    @classmethod
    def _deadline_iso(cls, v: str) -> str:
        return _validate_deadline(v)

    @field_validator("skills")
    @classmethod
    def _skill_bound(cls, v: list[str]) -> list[str]:
        for s in v:
            if len(s) > 60:
                raise ValueError("each skill must be at most 60 chars")
        return v

    @field_validator("rules")
    @classmethod
    def _rules_bound(cls, v: dict) -> dict:
        serialized = len(str(v))
        if serialized > 4000:
            raise ValueError("rules payload too large (max ~4k chars)")
        return v


class UpdateApplicationStatusInput(BaseModel):
    application_id: str = Field(min_length=1, max_length=64)
    new_status: str = Field(min_length=1, max_length=32)
    reason: str = Field(default="", max_length=500)
