# Unit tests for the deterministic eligibility engine — boundary cases included.

from app.services.eligibility import evaluate_eligibility

STUDENT = {
    "name": "Asha",
    "branch": "CSE",
    "cgpa": 7.4,
    "active_backlogs": 0,
    "graduation_year": 2026,
}

DRIVE = {
    "title": "Nimbus SDE",
    "rules": {
        "min_cgpa": 7.0,
        "max_backlogs": 0,
        "allowed_branches": ["CSE", "IT", "ECE"],
        "min_graduation_year": 2026,
        "max_graduation_year": 2027,
    },
}


def test_fully_eligible_student():
    r = evaluate_eligibility(STUDENT, DRIVE)
    assert r.eligible is True
    assert r.missing_requirements == []
    assert "All eligibility criteria are met" in r.reasons


def test_exact_cgpa_cutoff_passes():
    student = {**STUDENT, "cgpa": 7.0}
    r = evaluate_eligibility(student, DRIVE)
    assert r.eligible is True


def test_cgpa_just_below_cutoff_fails():
    student = {**STUDENT, "cgpa": 6.99}
    r = evaluate_eligibility(student, DRIVE)
    assert r.eligible is False
    assert "CGPA" in r.reasons[0]
    assert r.missing_requirements == ["CGPA >= 7.0"]


def test_exact_backlog_boundary_passes():
    drive = {"rules": {"max_backlogs": 1}}
    student = {**STUDENT, "active_backlogs": 1}
    r = evaluate_eligibility(student, drive)
    assert r.eligible is True


def test_one_backlog_over_limit_fails():
    drive = {"rules": {"max_backlogs": 0}}
    student = {**STUDENT, "active_backlogs": 1}
    r = evaluate_eligibility(student, drive)
    assert r.eligible is False
    assert "backlogs" in r.reasons[0]


def test_zero_backlogs_when_none_recorded():
    drive = {"rules": {"max_backlogs": 0}}
    student = {**STUDENT, "active_backlogs": None}
    r = evaluate_eligibility(student, drive)
    assert r.eligible is True  # None treated as 0


def test_branch_not_allowed():
    student = {**STUDENT, "branch": "Mechanical"}
    r = evaluate_eligibility(student, DRIVE)
    assert r.eligible is False
    assert "Mechanical" in r.reasons[0]
    assert "CSE" in r.missing_requirements[0]


def test_no_branch_restriction_allows_all():
    drive = {"rules": {"allowed_branches": None, "min_cgpa": 6.0}}
    student = {**STUDENT, "branch": "Civil", "cgpa": 6.5}
    r = evaluate_eligibility(student, drive)
    assert r.eligible is True


def test_missing_profile_fields_flagged():
    student = {"name": "New", "branch": None, "cgpa": None}
    r = evaluate_eligibility(student, DRIVE)
    assert r.eligible is False
    assert len(r.missing_requirements) == 2


def test_graduation_year_window():
    student = {**STUDENT, "graduation_year": 2025}
    r = evaluate_eligibility(student, DRIVE)
    assert r.eligible is False
    assert "2025" in r.reasons[0]


def test_multiple_failures_all_reported():
    student = {"branch": "Mechanical", "cgpa": 5.0, "active_backlogs": 2, "graduation_year": 2026}
    r = evaluate_eligibility(student, DRIVE)
    assert r.eligible is False
    assert len(r.reasons) == 3
    assert len(r.missing_requirements) == 3
