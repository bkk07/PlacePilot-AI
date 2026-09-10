# Seeded mock data backing the Phase 3 tools (real DB arrives in Phase 4/6).

STUDENTS = {
    "s-001": {
        "id": "s-001",
        "name": "Asha Verma",
        "branch": "CSE",
        "cgpa": 7.4,
        "active_backlogs": 0,
        "graduation_year": 2026,
        "skills": ["python", "sql", "aws"],
    },
    "s-002": {
        "id": "s-002",
        "name": "Rohan Iyer",
        "branch": "Mechanical",
        "cgpa": 6.2,
        "active_backlogs": 1,
        "graduation_year": 2026,
        "skills": ["python"],
    },
}

COMPANIES = {
    "c-001": {"id": "c-001", "name": "Nimbus Software", "industry": "Cloud Analytics"},
    "c-002": {"id": "c-002", "name": "QuantAlpha Analytics", "industry": "Quant Research"},
}

DRIVES = {
    "d-001": {
        "id": "d-001",
        "company_id": "c-001",
        "title": "Nimbus Software Engineer (2026 batch)",
        "role": "Software Engineer",
        "ctc_lpa": 12.0,
        "stipend_monthly": None,
        "location": "Bangalore",
        "application_deadline": "2026-10-01",
        "status": "open",
        "skills": ["python", "aws", "sql"],
        "rules": {"min_cgpa": 7.0, "max_backlogs": 0, "allowed_branches": ["CSE", "IT", "ECE"]},
    },
    "d-002": {
        "id": "d-002",
        "company_id": "c-002",
        "title": "QuantAlpha Data Analyst (2026 batch)",
        "role": "Data Analyst",
        "ctc_lpa": 9.5,
        "stipend_monthly": 35000,
        "location": "Mumbai",
        "application_deadline": "2026-09-20",
        "status": "open",
        "skills": ["sql", "python"],
        "rules": {"min_cgpa": 6.5, "max_backlogs": 1, "allowed_branches": None},
    },
    "d-003": {
        "id": "d-003",
        "company_id": "c-001",
        "title": "Nimbus DevOps Intern",
        "role": "DevOps Intern",
        "ctc_lpa": None,
        "stipend_monthly": 25000,
        "location": "Remote",
        "application_deadline": "2026-09-30",
        "status": "open",
        "skills": ["aws", "linux"],
        "rules": {"min_cgpa": 6.0, "max_backlogs": 1, "allowed_branches": None},
    },
}

APPLICATIONS = {
    "a-001": {"id": "a-001", "drive_id": "d-003", "student_id": "s-001", "status": "applied"},
    "a-002": {"id": "a-002", "drive_id": "d-001", "student_id": "s-002", "status": "shortlisted"},
    "a-003": {"id": "a-003", "drive_id": "d-002", "student_id": "s-001", "status": "rejected"},
}
