# Seed script: creates schema + demo users (student, admin), companies, drives, applications.
#
# Usage (from backend/):  python -m app.db.seed

import uuid

from passlib.context import CryptContext
from sqlalchemy import select

from app.core.security import create_token
from app.db.db import get_session_factory, init_db
from app.db.models import Application, Company, Drive, StudentProfile, User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

STUDENT_EMAIL = "asha@college.edu"
ADMIN_EMAIL = "placement@college.edu"
STUDENT_PASSWORD = "student-pass"
ADMIN_PASSWORD = "admin-pass"


def seed() -> None:
    init_db()
    session = get_session_factory()()
    try:
        if session.scalar(select(User).where(User.email == STUDENT_EMAIL)):
            print("Already seeded.")
            return

        student = User(
            email=STUDENT_EMAIL,
            password_hash=pwd.hash(STUDENT_PASSWORD),
            full_name="Asha Verma",
            role="student",
        )
        other_student = User(
            email="rohan@college.edu",
            password_hash=pwd.hash("rohan-pass"),
            full_name="Rohan Iyer",
            role="student",
        )
        admin = User(
            email=ADMIN_EMAIL,
            password_hash=pwd.hash(ADMIN_PASSWORD),
            full_name="Placement Cell",
            role="admin",
        )
        session.add_all([student, other_student, admin])
        session.flush()

        profile = StudentProfile(
            user_id=student.id,
            roll_number="CS2026-001",
            branch="CSE",
            graduation_year=2026,
            cgpa=7.4,
            active_backlogs=0,
            skills=["python", "sql", "aws"],
        )
        rohan_profile = StudentProfile(
            user_id=other_student.id,
            roll_number="ME2026-042",
            branch="Mechanical",
            graduation_year=2026,
            cgpa=6.2,
            active_backlogs=1,
            skills=["python"],
        )
        session.add_all([profile, rohan_profile])

        nimbus = Company(name="Nimbus Software", industry="Cloud Analytics")
        quantalpha = Company(name="QuantAlpha Analytics", industry="Quant Research")
        session.add_all([nimbus, quantalpha])
        session.flush()

        drives = [
            Drive(
                company_id=nimbus.id,
                title="Nimbus Software Engineer (2026 batch)",
                role="Software Engineer",
                ctc_lpa=12.0,
                location="Bangalore",
                application_deadline="2026-10-01",
                status="open",
                skills=["python", "aws", "sql"],
                rules={"min_cgpa": 7.0, "max_backlogs": 0, "allowed_branches": ["CSE", "IT", "ECE"]},
            ),
            Drive(
                company_id=quantalpha.id,
                title="QuantAlpha Data Analyst (2026 batch)",
                role="Data Analyst",
                ctc_lpa=9.5,
                stipend_monthly=35000,
                location="Mumbai",
                application_deadline="2026-09-20",
                status="open",
                skills=["sql", "python"],
                rules={"min_cgpa": 6.5, "max_backlogs": 1},
            ),
            Drive(
                company_id=nimbus.id,
                title="Nimbus DevOps Intern",
                role="DevOps Intern",
                stipend_monthly=25000,
                location="Remote",
                application_deadline="2026-09-30",
                status="open",
                skills=["aws", "linux"],
                rules={"min_cgpa": 6.0, "max_backlogs": 1},
            ),
        ]
        session.add_all(drives)
        session.flush()

        session.add_all(
            [
                Application(drive_id=drives[2].id, student_id=student.id, status="applied"),
                Application(drive_id=drives[0].id, student_id=other_student.id, status="shortlisted"),
            ]
        )
        session.commit()

        print(f"student: {student.id} (asha@college.edu / {STUDENT_PASSWORD})")
        print(f"other student: {other_student.id} (rohan@college.edu / rohan-pass)")
        print(f"admin: {admin.id} (placement@college.edu / {ADMIN_PASSWORD})")
        print()
        print("Dev tokens (24h):")
        print("student:", create_token(str(student.id), "student"))
        print("admin :", create_token(str(admin.id), "admin"))
    finally:
        session.close()


if __name__ == "__main__":
    seed()
