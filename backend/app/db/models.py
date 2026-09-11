# TNPC Placement Drive — Complete Domain Model (31 entities)
# SQLAlchemy 2.0 / PostgreSQL. Vectors live in Weaviate; uploaded files live in StoredFile.file_data (BYTEA).
# Existing entities (User, Student via StudentProfile, Branch) are referenced, not redefined where possible.

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class DriveType(str, enum.Enum):
    ON_CAMPUS = "ON_CAMPUS"
    OFF_CAMPUS = "OFF_CAMPUS"
    POOL_CAMPUS = "POOL_CAMPUS"
    VIRTUAL = "VIRTUAL"


class DriveStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    REGISTRATION_OPEN = "REGISTRATION_OPEN"
    REGISTRATION_CLOSED = "REGISTRATION_CLOSED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class DriveMode(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    HYBRID = "HYBRID"


class EmploymentType(str, enum.Enum):
    INTERNSHIP = "INTERNSHIP"
    FULL_TIME = "FULL_TIME"
    INTERNSHIP_TO_FULL_TIME = "INTERNSHIP_TO_FULL_TIME"
    CONTRACT = "CONTRACT"


class WorkMode(str, enum.Enum):
    ONSITE = "ONSITE"
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"


class SkillCategory(str, enum.Enum):
    PROGRAMMING_LANGUAGE = "PROGRAMMING_LANGUAGE"
    FRAMEWORK = "FRAMEWORK"
    DATABASE = "DATABASE"
    CLOUD = "CLOUD"
    DEVOPS = "DEVOPS"
    WEB = "WEB"
    MOBILE = "MOBILE"
    DATA = "DATA"
    AI_ML = "AI_ML"
    SOFT_SKILL = "SOFT_SKILL"
    TOOLS = "TOOLS"
    OTHER = "OTHER"


class SkillLevel(str, enum.Enum):
    BEGINNER = "BEGINNER"
    BASIC = "BASIC"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class EducationLevel(str, enum.Enum):
    TENTH = "TENTH"
    TWELFTH = "TWELFTH"
    DIPLOMA = "DIPLOMA"
    UNDERGRADUATE = "UNDERGRADUATE"
    POSTGRADUATE = "POSTGRADUATE"


class DriveRoundType(str, enum.Enum):
    APTITUDE = "APTITUDE"
    CODING = "CODING"
    GROUP_DISCUSSION = "GROUP_DISCUSSION"
    TECHNICAL_INTERVIEW = "TECHNICAL_INTERVIEW"
    MANAGERIAL_INTERVIEW = "MANAGERIAL_INTERVIEW"
    HR_INTERVIEW = "HR_INTERVIEW"
    MACHINE_CODING = "MACHINE_CODING"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"
    CASE_STUDY = "CASE_STUDY"
    ASSESSMENT = "ASSESSMENT"
    OTHER = "OTHER"


class RoundStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ApplicationStatus(str, enum.Enum):
    APPLIED = "APPLIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ELIGIBILITY_REJECTED = "ELIGIBILITY_REJECTED"
    SHORTLISTED = "SHORTLISTED"
    IN_PROCESS = "IN_PROCESS"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    OFFERED = "OFFERED"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    OFFER_DECLINED = "OFFER_DECLINED"


class ShortlistType(str, enum.Enum):
    ELIGIBILITY = "ELIGIBILITY"
    ASSESSMENT = "ASSESSMENT"
    TECHNICAL = "TECHNICAL"
    HR = "HR"
    FINAL = "FINAL"
    MANUAL = "MANUAL"


class RoundResultValue(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WAITLISTED = "WAITLISTED"
    ABSENT = "ABSENT"
    NOT_EVALUATED = "NOT_EVALUATED"
    DISQUALIFIED = "DISQUALIFIED"


class SelectionStatus(str, enum.Enum):
    SELECTED = "SELECTED"
    WAITLISTED = "WAITLISTED"
    CANCELLED = "CANCELLED"


class OfferStatus(str, enum.Enum):
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class AnnouncementType(str, enum.Enum):
    REGISTRATION_OPEN = "REGISTRATION_OPEN"
    REGISTRATION_CLOSING = "REGISTRATION_CLOSING"
    SHORTLIST_RELEASED = "SHORTLIST_RELEASED"
    ROUND_SCHEDULE = "ROUND_SCHEDULE"
    INTERVIEW_SCHEDULE = "INTERVIEW_SCHEDULE"
    RESULT = "RESULT"
    OFFER = "OFFER"
    GENERAL = "GENERAL"


class ContactType(str, enum.Enum):
    HR = "HR"
    RECRUITER = "RECRUITER"
    HIRING_MANAGER = "HIRING_MANAGER"
    COMPANY_COORDINATOR = "COMPANY_COORDINATOR"
    TNPC_COORDINATOR = "TNPC_COORDINATOR"


class OutcomeValue(str, enum.Enum):
    SELECTED = "SELECTED"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    OFFER_DECLINED = "OFFER_DECLINED"
    JOINED = "JOINED"
    DID_NOT_JOIN = "DID_NOT_JOIN"
    WAITLISTED = "WAITLISTED"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# Existing / shared entities
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    student_profile: Mapped["StudentProfile"] = relationship(back_populates="user", uselist=False)


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    roll_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    branch: Mapped[str] = mapped_column(String, nullable=False)
    graduation_year: Mapped[int] = mapped_column(Integer, nullable=False)
    cgpa: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    active_backlogs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    # --- student information ---
    personal_email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_photo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stored_files.id"), nullable=True)
    # --- B.Tech academic information ---
    degree: Mapped[str] = mapped_column(String, default="B.Tech", nullable=False)
    specialization: Mapped[str | None] = mapped_column(String, nullable=True)
    admission_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_semester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # --- school academic details ---
    tenth_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    tenth_board: Mapped[str | None] = mapped_column(String, nullable=True)
    twelfth_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    twelfth_board: Mapped[str | None] = mapped_column(String, nullable=True)
    diploma_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    # --- backlog / academic eligibility ---
    history_of_backlogs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    year_gaps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="student_profile")
    profile_photo: Mapped["StoredFile"] = relationship(foreign_keys=[profile_photo_id])


class Branch(Base):
    """Reference branch/department. Seed with CSE, IT, ECE, etc. if not present."""
    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ---------------------------------------------------------------------------
# 24. StoredFile — must be defined early (referenced by Company, DriveDocument...)
# ---------------------------------------------------------------------------
class StoredFile(Base):
    __tablename__ = "stored_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ---------------------------------------------------------------------------
# 1. Company
# ---------------------------------------------------------------------------
class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    company_size: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    headquarters: Mapped[str | None] = mapped_column(String, nullable=True)
    logo_file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stored_files.id"), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    logo_file: Mapped["StoredFile"] = relationship(foreign_keys=[logo_file_id])
    drives: Mapped[list["Drive"]] = relationship(back_populates="company")


# ---------------------------------------------------------------------------
# 2. Drive
# ---------------------------------------------------------------------------
class Drive(Base):
    __tablename__ = "drives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    drive_type: Mapped[str] = mapped_column(String, default=DriveType.ON_CAMPUS.value)
    status: Mapped[str] = mapped_column(String, default=DriveStatus.DRAFT.value)
    registration_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    drive_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    drive_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mode: Mapped[str] = mapped_column(String, default=DriveMode.OFFLINE.value)
    venue: Mapped[str | None] = mapped_column(String, nullable=True)
    meeting_link: Mapped[str | None] = mapped_column(String, nullable=True)
    application_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # legacy simple fields kept for backward compat with Phase 6 code
    role: Mapped[str] = mapped_column(String, nullable=False, default="Software Engineer")
    ctc_lpa: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    stipend_monthly: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=False, default="Bangalore")
    application_deadline: Mapped[str] = mapped_column(String, nullable=False, default="2026-12-31")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    rules: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    company: Mapped["Company"] = relationship(back_populates="drives")
    job_positions: Mapped[list["JobPosition"]] = relationship(back_populates="drive", cascade="all, delete-orphan")
    eligibility_criteria: Mapped["EligibilityCriteria"] = relationship(back_populates="drive", uselist=False, cascade="all, delete-orphan")
    eligible_branches: Mapped[list["DriveEligibleBranch"]] = relationship(back_populates="drive", cascade="all, delete-orphan")
    eligible_batches: Mapped[list["DriveEligibleBatch"]] = relationship(back_populates="drive", cascade="all, delete-orphan")
    rounds: Mapped[list["DriveRound"]] = relationship(back_populates="drive", cascade="all, delete-orphan")
    schedules: Mapped[list["DriveSchedule"]] = relationship(back_populates="drive", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="drive")
    documents: Mapped[list["DriveDocument"]] = relationship(back_populates="drive", cascade="all, delete-orphan")
    document_requirements: Mapped[list["DriveDocumentRequirement"]] = relationship(back_populates="drive", cascade="all, delete-orphan")
    announcements: Mapped[list["DriveAnnouncement"]] = relationship(back_populates="drive", cascade="all, delete-orphan")
    contacts: Mapped[list["DriveContact"]] = relationship(back_populates="drive", cascade="all, delete-orphan")
    policy: Mapped["DrivePolicy"] = relationship(back_populates="drive", uselist=False, cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# 3. JobPosition
# ---------------------------------------------------------------------------
class JobPosition(Base):
    __tablename__ = "job_positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    department: Mapped[str | None] = mapped_column(String, nullable=True)
    employment_type: Mapped[str] = mapped_column(String, default=EmploymentType.FULL_TIME.value)
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    openings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    drive: Mapped["Drive"] = relationship(back_populates="job_positions")
    skills: Mapped[list["JobPositionSkill"]] = relationship(back_populates="job_position", cascade="all, delete-orphan")
    compensation: Mapped["Compensation"] = relationship(back_populates="job_position", uselist=False, cascade="all, delete-orphan")
    internship_details: Mapped["InternshipDetails"] = relationship(back_populates="job_position", uselist=False, cascade="all, delete-orphan")
    experience_requirement: Mapped["ExperienceRequirement"] = relationship(back_populates="job_position", uselist=False, cascade="all, delete-orphan")
    certification_requirements: Mapped[list["JobCertificationRequirement"]] = relationship(back_populates="job_position", cascade="all, delete-orphan")
    locations: Mapped[list["JobLocation"]] = relationship(back_populates="job_position", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# 4. Skill
# ---------------------------------------------------------------------------
class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String, default=SkillCategory.OTHER.value)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    job_position_skills: Mapped[list["JobPositionSkill"]] = relationship(back_populates="skill")


# ---------------------------------------------------------------------------
# 5. JobPositionSkill
# ---------------------------------------------------------------------------
class JobPositionSkill(Base):
    __tablename__ = "job_position_skills"
    __table_args__ = (UniqueConstraint("job_position_id", "skill_id", name="uq_jp_skill"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_position_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_positions.id"), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    skill_level: Mapped[str | None] = mapped_column(String, nullable=True)
    minimum_experience_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    job_position: Mapped["JobPosition"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(back_populates="job_position_skills")


# ---------------------------------------------------------------------------
# 6. EligibilityCriteria
# ---------------------------------------------------------------------------
class EligibilityCriteria(Base):
    __tablename__ = "eligibility_criteria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), unique=True, nullable=False)
    minimum_cgpa: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    maximum_cgpa: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    minimum_10th_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    minimum_12th_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    minimum_diploma_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    passing_year_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passing_year_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    backlogs_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    maximum_backlogs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_backlogs_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    education_gap_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    maximum_education_gap_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimum_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maximum_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    additional_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    drive: Mapped["Drive"] = relationship(back_populates="eligibility_criteria")


# ---------------------------------------------------------------------------
# 7. EducationRequirement
# ---------------------------------------------------------------------------
class EducationRequirement(Base):
    __tablename__ = "education_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("drives.id"), nullable=True)
    job_position_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("job_positions.id"), nullable=True)
    education_level: Mapped[str] = mapped_column(String, nullable=False)
    minimum_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    minimum_cgpa: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    drive: Mapped["Drive"] = relationship()
    job_position: Mapped["JobPosition"] = relationship()


# ---------------------------------------------------------------------------
# 8. DriveEligibleBranch
# ---------------------------------------------------------------------------
class DriveEligibleBranch(Base):
    __tablename__ = "drive_eligible_branches"
    __table_args__ = (UniqueConstraint("drive_id", "branch_id", name="uq_drive_branch"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)

    drive: Mapped["Drive"] = relationship(back_populates="eligible_branches")
    branch: Mapped["Branch"] = relationship()


# ---------------------------------------------------------------------------
# 9. DriveEligibleBatch
# ---------------------------------------------------------------------------
class DriveEligibleBatch(Base):
    __tablename__ = "drive_eligible_batches"
    __table_args__ = (UniqueConstraint("drive_id", "graduation_year", name="uq_drive_batch"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    graduation_year: Mapped[int] = mapped_column(Integer, nullable=False)

    drive: Mapped["Drive"] = relationship(back_populates="eligible_batches")


# ---------------------------------------------------------------------------
# 10. ExperienceRequirement
# ---------------------------------------------------------------------------
class ExperienceRequirement(Base):
    __tablename__ = "experience_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_position_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_positions.id"), unique=True, nullable=False)
    minimum_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maximum_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    freshers_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    job_position: Mapped["JobPosition"] = relationship(back_populates="experience_requirement")


# ---------------------------------------------------------------------------
# 11. Certification
# ---------------------------------------------------------------------------
class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    issuing_organization: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    job_requirements: Mapped[list["JobCertificationRequirement"]] = relationship(back_populates="certification")


# ---------------------------------------------------------------------------
# 12. JobCertificationRequirement
# ---------------------------------------------------------------------------
class JobCertificationRequirement(Base):
    __tablename__ = "job_certification_requirements"
    __table_args__ = (UniqueConstraint("job_position_id", "certification_id", name="uq_jp_cert"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_position_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_positions.id"), nullable=False)
    certification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("certifications.id"), nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)

    job_position: Mapped["JobPosition"] = relationship(back_populates="certification_requirements")
    certification: Mapped["Certification"] = relationship(back_populates="job_requirements")


# ---------------------------------------------------------------------------
# 13. Compensation
# ---------------------------------------------------------------------------
class Compensation(Base):
    __tablename__ = "compensations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_position_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_positions.id"), unique=True, nullable=False)
    annual_ctc: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    fixed_ctc: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    variable_ctc: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    monthly_salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    monthly_stipend: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    joining_bonus: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    retention_bonus: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String, default="INR")

    job_position: Mapped["JobPosition"] = relationship(back_populates="compensation")


# ---------------------------------------------------------------------------
# 14. InternshipDetails
# ---------------------------------------------------------------------------
class InternshipDetails(Base):
    __tablename__ = "internship_details"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_position_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_positions.id"), unique=True, nullable=False)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paid: Mapped[bool] = mapped_column(Boolean, default=True)
    stipend: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    ppo_available: Mapped[bool] = mapped_column(Boolean, default=False)
    ppo_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)

    job_position: Mapped["JobPosition"] = relationship(back_populates="internship_details")


# ---------------------------------------------------------------------------
# 15. JobLocation
# ---------------------------------------------------------------------------
class JobLocation(Base):
    __tablename__ = "job_locations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_position_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_positions.id"), nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str] = mapped_column(String, default="India")
    work_mode: Mapped[str | None] = mapped_column(String, nullable=True)

    job_position: Mapped["JobPosition"] = relationship(back_populates="locations")


# ---------------------------------------------------------------------------
# 16. DriveRound
# ---------------------------------------------------------------------------
class DriveRound(Base):
    __tablename__ = "drive_rounds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eliminatory: Mapped[bool] = mapped_column(Boolean, default=True)
    passing_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    status: Mapped[str] = mapped_column(String, default=RoundStatus.SCHEDULED.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    drive: Mapped["Drive"] = relationship(back_populates="rounds")
    assessment_config: Mapped["AssessmentConfiguration"] = relationship(back_populates="round", uselist=False, cascade="all, delete-orphan")
    results: Mapped[list["RoundResult"]] = relationship(back_populates="round")


# ---------------------------------------------------------------------------
# 17. AssessmentConfiguration
# ---------------------------------------------------------------------------
class AssessmentConfiguration(Base):
    __tablename__ = "assessment_configurations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drive_rounds.id"), unique=True, nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_questions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coding_questions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mcq_questions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passing_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    negative_marking: Mapped[bool] = mapped_column(Boolean, default=False)
    assessment_platform: Mapped[str | None] = mapped_column(String, nullable=True)
    assessment_url: Mapped[str | None] = mapped_column(String, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    round: Mapped["DriveRound"] = relationship(back_populates="assessment_config")


# ---------------------------------------------------------------------------
# 18. DriveSchedule
# ---------------------------------------------------------------------------
class DriveSchedule(Base):
    __tablename__ = "drive_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    event_name: Mapped[str] = mapped_column(String, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    venue: Mapped[str | None] = mapped_column(String, nullable=True)
    meeting_link: Mapped[str | None] = mapped_column(String, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    drive: Mapped["Drive"] = relationship(back_populates="schedules")


# ---------------------------------------------------------------------------
# 19. DriveApplication
# ---------------------------------------------------------------------------
class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("drive_id", "student_id", "job_position_id", name="uq_application"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    job_position_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("job_positions.id"), nullable=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default=ApplicationStatus.APPLIED.value)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    eligibility_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    eligible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    eligibility_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    drive: Mapped["Drive"] = relationship(back_populates="applications")
    job_position: Mapped["JobPosition"] = relationship()
    history: Mapped[list["ApplicationStatusHistory"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    shortlists: Mapped[list["DriveShortlist"]] = relationship(back_populates="application")
    round_results: Mapped[list["RoundResult"]] = relationship(back_populates="application")
    selection: Mapped["DriveSelection"] = relationship(back_populates="application", uselist=False)
    documents: Mapped[list["ApplicationDocument"]] = relationship(back_populates="application", cascade="all, delete-orphan")


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String, nullable=True)
    to_status: Mapped[str] = mapped_column(String, nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    application: Mapped["Application"] = relationship(back_populates="history")


# ---------------------------------------------------------------------------
# 20. DriveShortlist
# ---------------------------------------------------------------------------
class DriveShortlist(Base):
    __tablename__ = "drive_shortlists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    shortlist_type: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    shortlisted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    drive: Mapped["Drive"] = relationship()
    application: Mapped["Application"] = relationship(back_populates="shortlists")
    student: Mapped["User"] = relationship(foreign_keys=[student_id])


# ---------------------------------------------------------------------------
# 21. RoundResult
# ---------------------------------------------------------------------------
class RoundResult(Base):
    __tablename__ = "round_results"
    __table_args__ = (UniqueConstraint("application_id", "round_id", name="uq_app_round"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False)
    round_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drive_rounds.id"), nullable=False)
    result: Mapped[str] = mapped_column(String, default=RoundResultValue.NOT_EVALUATED.value)
    score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    application: Mapped["Application"] = relationship(back_populates="round_results")
    round: Mapped["DriveRound"] = relationship(back_populates="results")


# ---------------------------------------------------------------------------
# 22. DriveSelection
# ---------------------------------------------------------------------------
class DriveSelection(Base):
    __tablename__ = "drive_selections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), unique=True, nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    job_position_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_positions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default=SelectionStatus.SELECTED.value)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    drive: Mapped["Drive"] = relationship()
    application: Mapped["Application"] = relationship(back_populates="selection")
    job_position: Mapped["JobPosition"] = relationship()
    offer: Mapped["DriveOffer"] = relationship(back_populates="selection", uselist=False, cascade="all, delete-orphan")
    outcome: Mapped["PlacementOutcome"] = relationship(back_populates="selection", uselist=False)


# ---------------------------------------------------------------------------
# 23. DriveOffer
# ---------------------------------------------------------------------------
class DriveOffer(Base):
    __tablename__ = "drive_offers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    selection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drive_selections.id"), unique=True, nullable=False)
    offered_ctc: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    offered_stipend: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    joining_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    offer_status: Mapped[str] = mapped_column(String, default=OfferStatus.OFFERED.value)
    offer_letter_file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stored_files.id"), nullable=True)
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    declined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    selection: Mapped["DriveSelection"] = relationship(back_populates="offer")
    offer_letter_file: Mapped["StoredFile"] = relationship()


# ---------------------------------------------------------------------------
# 25. DriveDocument
# ---------------------------------------------------------------------------
class DriveDocument(Base):
    __tablename__ = "drive_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    stored_file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stored_files.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    drive: Mapped["Drive"] = relationship(back_populates="documents")
    stored_file: Mapped["StoredFile"] = relationship()


# ---------------------------------------------------------------------------
# 26. DriveDocumentRequirement
# ---------------------------------------------------------------------------
class DriveDocumentRequirement(Base):
    __tablename__ = "drive_document_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    drive: Mapped["Drive"] = relationship(back_populates="document_requirements")


# ---------------------------------------------------------------------------
# 27. ApplicationDocument
# ---------------------------------------------------------------------------
class ApplicationDocument(Base):
    __tablename__ = "application_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False)
    stored_file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stored_files.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    verification_status: Mapped[str] = mapped_column(String, default=VerificationStatus.PENDING.value)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    application: Mapped["Application"] = relationship(back_populates="documents")
    stored_file: Mapped["StoredFile"] = relationship()


# ---------------------------------------------------------------------------
# 28. DriveAnnouncement
# ---------------------------------------------------------------------------
class DriveAnnouncement(Base):
    __tablename__ = "drive_announcements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    announcement_type: Mapped[str] = mapped_column(String, default=AnnouncementType.GENERAL.value)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    published_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    drive: Mapped["Drive"] = relationship(back_populates="announcements")


# ---------------------------------------------------------------------------
# 29. DriveContact
# ---------------------------------------------------------------------------
class DriveContact(Base):
    __tablename__ = "drive_contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    designation: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_type: Mapped[str] = mapped_column(String, nullable=False)

    drive: Mapped["Drive"] = relationship(back_populates="contacts")


# ---------------------------------------------------------------------------
# 30. DrivePolicy
# ---------------------------------------------------------------------------
class DrivePolicy(Base):
    __tablename__ = "drive_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), unique=True, nullable=False)
    one_job_per_student: Mapped[bool] = mapped_column(Boolean, default=False)
    one_company_per_student: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_students_with_existing_offers: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_withdrawal: Mapped[bool] = mapped_column(Boolean, default=True)
    require_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    placement_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    withdrawal_policy: Mapped[str | None] = mapped_column(Text, nullable=True)

    drive: Mapped["Drive"] = relationship(back_populates="policy")


# ---------------------------------------------------------------------------
# 31. PlacementOutcome
# ---------------------------------------------------------------------------
class PlacementOutcome(Base):
    __tablename__ = "placement_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drive_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drives.id"), nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), unique=True, nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    selection_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("drive_selections.id"), nullable=True)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    package_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    joining_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    drive: Mapped["Drive"] = relationship()
    application: Mapped["Application"] = relationship()
    selection: Mapped["DriveSelection"] = relationship(back_populates="outcome")


# ---------------------------------------------------------------------------
# AuditLog (cross-cutting, kept from Phase 4)
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String, nullable=True)
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    args: Mapped[dict] = mapped_column(JSON, default=dict)
    result_status: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
