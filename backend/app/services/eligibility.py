# Eligibility engine — the single source of truth for eligibility decisions.
# Pure function: student profile + drive rules in -> eligible/not-eligible + reasons out.
# The LLM never determines eligibility; it only explains this engine's result.

from dataclasses import dataclass, field


@dataclass
class EligibilityResult:
    eligible: bool
    reasons: list[str] = field(default_factory=list)
    missing_requirements: list[str] = field(default_factory=list)


def evaluate_eligibility(student: dict, drive: dict) -> EligibilityResult:
    """Evaluate a student against a drive's eligibility rules. Exact cutoffs pass."""
    rules = drive.get("rules") or {}
    reasons: list[str] = []
    missing: list[str] = []
    eligible = True

    min_cgpa = rules.get("min_cgpa")
    if min_cgpa is not None:
        cgpa = student.get("cgpa")
        if cgpa is None:
            eligible = False
            reasons.append("CGPA is not filled in on the student profile")
            missing.append(f"CGPA >= {min_cgpa} (profile has no CGPA)")
        elif cgpa < min_cgpa:
            eligible = False
            reasons.append(f"CGPA {cgpa:.2f} is below the required minimum {min_cgpa:.2f}")
            missing.append(f"CGPA >= {min_cgpa}")

    max_backlogs = rules.get("max_backlogs")
    if max_backlogs is not None:
        backlogs = student.get("active_backlogs", 0) or 0
        if backlogs > max_backlogs:
            eligible = False
            reasons.append(f"{backlogs} active backlogs exceed the allowed maximum of {max_backlogs}")
            missing.append(f"Active backlogs <= {max_backlogs}")

    allowed_branches = rules.get("allowed_branches")
    if allowed_branches:
        branch = student.get("branch")
        if branch is None:
            eligible = False
            reasons.append("Branch is not filled in on the student profile")
            missing.append(f"Branch in {allowed_branches} (profile has no branch)")
        elif branch not in allowed_branches:
            eligible = False
            reasons.append(f"Branch {branch} is not in the allowed list: {', '.join(allowed_branches)}")
            missing.append(f"Branch in {', '.join(allowed_branches)}")

    min_year = rules.get("min_graduation_year")
    max_year = rules.get("max_graduation_year")
    grad_year = student.get("graduation_year")
    if grad_year is not None and (min_year is not None or max_year is not None):
        if min_year is not None and grad_year < min_year:
            eligible = False
            reasons.append(f"Graduation year {grad_year} is before the required {min_year}")
            missing.append(f"Graduation year >= {min_year}")
        if max_year is not None and grad_year > max_year:
            eligible = False
            reasons.append(f"Graduation year {grad_year} is after the allowed {max_year}")
            missing.append(f"Graduation year <= {max_year}")

    if eligible and not reasons:
        reasons.append("All eligibility criteria are met")

    return EligibilityResult(eligible=eligible, reasons=reasons, missing_requirements=missing)
