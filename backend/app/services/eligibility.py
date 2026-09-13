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
    """Evaluate a student against a drive's eligibility rules. Exact cutoffs pass.
    Merges legacy drive.rules with normalized TNPC criteria passed as extended keys.
    """
    rules = drive.get("rules") or {}
    # extended keys populated from EligibilityCriteria/Branch/Batch tables
    extended = drive.get("extended") or {}
    # merge extended into rules with priority to explicit extended values
    for k, v in extended.items():
        if v is not None and rules.get(k) is None:
            rules[k] = v

    reasons: list[str] = []
    missing: list[str] = []
    eligible = True

    # CGPA - supports min_cgpa / minimum_cgpa
    min_cgpa = rules.get("min_cgpa") if rules.get("min_cgpa") is not None else rules.get("minimum_cgpa")
    if min_cgpa is not None:
        try:
            min_cgpa = float(min_cgpa)
        except Exception:
            min_cgpa = None
    if min_cgpa is not None:
        cgpa = student.get("cgpa")
        if cgpa is None:
            eligible = False
            reasons.append("CGPA is not filled in on the student profile")
            missing.append(f"CGPA >= {min_cgpa} (profile has no CGPA)")
        elif float(cgpa) < min_cgpa:
            eligible = False
            reasons.append(f"CGPA {float(cgpa):.2f} is below the required minimum {min_cgpa:.2f}")
            missing.append(f"CGPA >= {min_cgpa}")

    max_backlogs = rules.get("max_backlogs") if rules.get("max_backlogs") is not None else rules.get("maximum_backlogs")
    if max_backlogs is not None:
        try:
            max_backlogs = int(max_backlogs)
        except Exception:
            max_backlogs = None
    if max_backlogs is not None:
        backlogs = student.get("active_backlogs", 0) or 0
        if int(backlogs) > max_backlogs:
            eligible = False
            reasons.append(f"{backlogs} active backlogs exceed the allowed maximum of {max_backlogs}")
            missing.append(f"Active backlogs <= {max_backlogs}")

    # Backlogs allowed flag
    if rules.get("backlogs_allowed") is False and (student.get("active_backlogs", 0) or 0) > 0:
        eligible = False
        reasons.append("No active backlogs allowed for this drive")
        missing.append("Active backlogs must be 0")

    allowed_branches = rules.get("allowed_branches") or rules.get("eligible_branches") or extended.get("eligible_branches")
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

    min_year = rules.get("min_graduation_year") if rules.get("min_graduation_year") is not None else rules.get("passing_year_from")
    max_year = rules.get("max_graduation_year") if rules.get("max_graduation_year") is not None else rules.get("passing_year_to")
    grad_year = student.get("graduation_year")
    # also handle eligible_batches list
    eligible_batches = rules.get("eligible_batches") or extended.get("eligible_batches")
    if eligible_batches and grad_year is not None:
        if grad_year not in eligible_batches:
            eligible = False
            reasons.append(f"Graduation year {grad_year} not in eligible batches {eligible_batches}")
            missing.append(f"Graduation year in {eligible_batches}")
    elif grad_year is not None and (min_year is not None or max_year is not None):
        if min_year is not None and grad_year < int(min_year):
            eligible = False
            reasons.append(f"Graduation year {grad_year} is before the required {min_year}")
            missing.append(f"Graduation year >= {min_year}")
        if max_year is not None and grad_year > int(max_year):
            eligible = False
            reasons.append(f"Graduation year {grad_year} is after the allowed {max_year}")
            missing.append(f"Graduation year <= {max_year}")

    # 10th / 12th / diploma percentage checks
    for key, student_key, label in [
        ("minimum_10th_percentage", "tenth_percentage", "10th percentage"),
        ("minimum_12th_percentage", "twelfth_percentage", "12th percentage"),
        ("minimum_diploma_percentage", "diploma_percentage", "Diploma percentage"),
    ]:
        min_pct = rules.get(key)
        if min_pct is not None:
            try:
                min_pct = float(min_pct)
            except Exception:
                continue
            val = student.get(student_key)
            if val is None:
                eligible = False
                reasons.append(f"{label} not filled but required >= {min_pct}")
                missing.append(f"{label} >= {min_pct}")
            elif float(val) < min_pct:
                eligible = False
                reasons.append(f"{label} {float(val):.1f}% below required {min_pct:.1f}%")
                missing.append(f"{label} >= {min_pct}")

    if eligible and not reasons:
        reasons.append("All eligibility criteria are met")

    return EligibilityResult(eligible=eligible, reasons=reasons, missing_requirements=missing)
