# Unit tests for agent tools: results, authz-relevant behavior, and input validation.

from app.agent.tools import execute_tool, get_recommendations, search_drives


def test_search_drives_by_company():
    results = search_drives(company="Nimbus")
    assert len(results) == 2
    assert all("Nimbus" in d["title"] for d in results)


def test_search_drives_by_role():
    results = search_drives(role="Data Analyst")
    assert len(results) == 1
    assert results[0]["id"] == "d-002"


def test_search_drives_free_text():
    results = search_drives(query="python")
    assert len(results) == 2  # d-001 and d-002 list python as a skill


def test_search_drives_no_match():
    assert search_drives(company="Nonexistent") == []


def test_search_drives_hides_internal_rules():
    results = search_drives(company="Nimbus")
    assert all("rules" not in d for d in results)


def test_check_eligibility_by_exact_drive_id():
    r = execute_tool("check_eligibility", {"student_id": "s-001", "drive_id": "d-001"})
    assert r["eligible"] is True
    assert r["drive_id"] == "d-001"


def test_check_eligibility_resolves_drive_name():
    r = execute_tool("check_eligibility", {"student_id": "s-001", "drive": "QuantAlpha"})
    assert r["drive_id"] == "d-002"
    assert r["eligible"] is True  # Asha: cgpa 7.4 >= 6.5, branch unrestricted


def test_check_eligibility_resolved_drive_still_enforces_rules():
    r = execute_tool("check_eligibility", {"student_id": "s-002", "drive": "QuantAlpha"})
    assert r["drive_id"] == "d-002"
    assert r["eligible"] is False  # Rohan: cgpa 6.2 < 6.5
    assert any("CGPA" in reason for reason in r["reasons"])


def test_check_eligibility_ineligible_reasons():
    r = execute_tool("check_eligibility", {"student_id": "s-002", "drive_id": "d-001"})
    assert r["eligible"] is False
    assert any("CGPA" in reason for reason in r["reasons"])
    assert r["missing_requirements"]


def test_check_eligibility_unknown_student():
    r = execute_tool("check_eligibility", {"student_id": "s-999", "drive_id": "d-001"})
    assert "error" in r


def test_get_student_profile():
    r = execute_tool("get_student_profile", {"student_id": "s-001"})
    assert r["name"] == "Asha Verma"
    assert r["skills"] == ["python", "sql", "aws"]


def test_get_application_status_only_own():
    r = execute_tool("get_application_status", {"student_id": "s-001"})
    assert all(a["drive_title"] for a in r)
    assert len(r) == 2  # s-001 has a-001 (d-003) and a-003 (d-002)
    other = execute_tool("get_application_status", {"student_id": "s-002"})
    assert other[0]["drive_id"] == "d-001"


def test_get_drive_details_includes_rules():
    r = execute_tool("get_drive_details", {"drive_id": "d-001"})
    assert r["rules"]["min_cgpa"] == 7.0


def test_get_recommendations_ranked():
    r = get_recommendations("s-001")
    assert len(r) == 3
    scores = [d["score"] for d in r]
    assert scores == sorted(scores, reverse=True)
    assert r[0]["eligible"] is True


def test_execute_tool_rejects_unknown_tool():
    r = execute_tool("delete_everything", {})
    assert r["error"] == "unknown tool: delete_everything"


def test_execute_tool_rejects_unknown_args():
    r = execute_tool("get_student_profile", {"student_id": "s-001", "inject": "1; DROP TABLE"})
    assert "unknown arguments" in r["error"]


def test_execute_tool_never_raises():
    # bad arg types degrade to an error dict, not an exception
    r = execute_tool("search_drives", {"query": 123})
    assert isinstance(r, (list, dict))
