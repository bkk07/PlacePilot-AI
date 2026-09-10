# ER Model (PostgreSQL — relational entities only)

Vector data (chunk text + embeddings) lives in **Weaviate**, not Postgres. The `documents` table below stores metadata only; Weaviate chunks reference it via a `document_id` metadata field.

## Tables & relationships

```
users (PK id)
 ├── 1:1 ── student_profiles (PK user_id → users.id, UNIQUE)
 ├── 1:N ── applications (PK id, FK student_id → users.id)
 ├── 1:N ── documents (FK uploaded_by → users.id)
 ├── 1:N ── notifications (FK user_id → users.id)
 └── 1:1 ── notification_preferences (PK user_id → users.id)

companies (PK id)
 ├── 1:N ── drives (FK company_id → companies.id)
 ├── 1:N ── documents (FK company_id → companies.id, NULLABLE)
 └── M:N ── student_profiles.preferred_roles (stored as JSON/array on profile)

drives (PK id, FK company_id → companies.id)
 ├── 1:N ── drive_eligibility_rules (FK drive_id → drives.id)
 ├── 1:N ── drive_skills (M:N drive ↔ skills, FK skill_id → skills.id)
 └── 1:N ── applications (FK drive_id → drives.id)

applications (PK id, FK drive_id → drives.id, FK student_id → users.id)
 └── 1:N ── application_status_history (FK application_id → applications.id)

skills (PK id)
 ├── M:N ── student_skills (FK student_id → student_profiles.user_id, FK skill_id → skills.id)
 └── M:N ── drive_skills (FK drive_id → drives.id, FK skill_id → skills.id)

placement_statistics (PK id)          # aggregate/derived, no FKs (or optional FK to companies/branches)
interview_experiences (PK id, FK company_id → companies.id, FK author_id → users.id)  # text body; chunked into Weaviate
```

## Table definitions

### users
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email | VARCHAR UNIQUE | |
| password_hash | VARCHAR | |
| full_name | VARCHAR | |
| role | ENUM('student','admin','alumni') | alumni = future, schema-only |
| is_active | BOOLEAN | |
| created_at / updated_at | TIMESTAMP | |

### student_profiles
| Column | Type | Notes |
|---|---|---|
| user_id | UUID PK, FK → users.id | 1:1 |
| roll_number | VARCHAR UNIQUE | |
| branch | VARCHAR | |
| graduation_year | INTEGER | |
| cgpa | NUMERIC(4,2) | |
| active_backlogs | INTEGER, DEFAULT 0 | |
| resume_url | VARCHAR, NULLABLE | |
| preferred_roles | JSONB | array of role strings |
| created_at / updated_at | TIMESTAMP | |

### companies
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR UNIQUE | |
| industry | VARCHAR, NULLABLE | |
| website | VARCHAR, NULLABLE | |
| created_at / updated_at | TIMESTAMP | |

### drives
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| company_id | UUID FK → companies.id | |
| title | VARCHAR | e.g. "Software Engineer — 2026 batch" |
| role | VARCHAR | |
| job_description | TEXT | |
| ctc_lpa | NUMERIC(6,2) | |
| stipend_monthly | NUMERIC(8,2), NULLABLE | internship stipend |
| drive_type | ENUM('full_time','internship','internship_plus_ft') | |
| location | VARCHAR | |
| application_deadline | TIMESTAMP | |
| status | ENUM('upcoming','open','closed','completed') | |
| created_by | UUID FK → users.id | admin who created it |
| created_at / updated_at | TIMESTAMP | |

### drive_eligibility_rules
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| drive_id | UUID FK → drives.id | |
| min_cgpa | NUMERIC(4,2), NULLABLE | |
| max_backlogs | INTEGER, NULLABLE | |
| allowed_branches | JSONB | array of branch strings |
| min_graduation_year / max_graduation_year | INTEGER, NULLABLE | |
| other_criteria | TEXT, NULLABLE | free-text notes, never parsed by the rule engine |

### applications
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| drive_id | UUID FK → drives.id | |
| student_id | UUID FK → users.id | |
| status | ENUM('not_applied','applied','shortlisted','interview','offer','selected','rejected','withdrawn') | strict state machine |
| idempotency_key | VARCHAR UNIQUE | prevents duplicate submissions on retry |
| applied_at | TIMESTAMP, NULLABLE | |
| created_at / updated_at | TIMESTAMP | |
| UNIQUE(drive_id, student_id) | | one application per student per drive |

### application_status_history
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| application_id | UUID FK → applications.id | |
| from_status / to_status | application_status ENUM | |
| changed_by | UUID FK → users.id | |
| reason | TEXT, NULLABLE | |
| created_at | TIMESTAMP | |

### placement_statistics
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| branch | VARCHAR, NULLABLE | |
| graduation_year | INTEGER | |
| total_eligible / total_placed | INTEGER | |
| average_ctc_lpa / highest_ctc_lpa | NUMERIC(6,2) | |
| updated_at | TIMESTAMP | |

### interview_experiences
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| company_id | UUID FK → companies.id | |
| author_id | UUID FK → users.id | alumni (future) or student |
| role | VARCHAR | |
| body | TEXT | full text; chunks + embeddings go to Weaviate |
| created_at | TIMESTAMP | |

### documents  (metadata only)
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| title | VARCHAR | |
| company_id | UUID FK → companies.id, NULLABLE | |
| document_type | ENUM('placement_policy','job_description','interview_experience','other') | |
| file_path | VARCHAR | |
| uploaded_by | UUID FK → users.id | |
| uploaded_at | TIMESTAMP | |

Chunks (text + vector) live in the Weaviate `DocumentChunk` collection with metadata: `document_id`, `company`, `year`, `document_type`, `role`, `source`, `page_number`.

### notifications
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id | |
| notification_type | VARCHAR | new_drive / deadline / status_change |
| payload | JSONB | |
| is_read | BOOLEAN | |
| idempotency_key | VARCHAR UNIQUE | dispatch dedupe |
| created_at | TIMESTAMP | |

### notification_preferences
| Column | Type | Notes |
|---|---|---|
| user_id | UUID PK, FK → users.id | 1:1 |
| email_enabled | BOOLEAN, DEFAULT true | |
| in_app_enabled | BOOLEAN, DEFAULT true | |
| opt_out_types | JSONB | array of types to suppress |

### skills
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR UNIQUE | lowercase canonical, e.g. "python" |

### student_skills
| Column | Type | Notes |
|---|---|---|
| student_id | UUID FK → student_profiles.user_id | composite PK part |
| skill_id | UUID FK → skills.id | composite PK part |
| proficiency | INTEGER, NULLABLE | 1–5 |

### drive_skills
| Column | Type | Notes |
|---|---|---|
| drive_id | UUID FK → drives.id | composite PK part |
| skill_id | UUID FK → skills.id | composite PK part |
| is_required | BOOLEAN, DEFAULT true | |

## Design notes

- **No `document_chunks` table** — chunk text + embeddings live in Weaviate, keyed to `documents.id`.
- **State machine on applications** enforced in the service layer (Phase 6); the history table is append-only.
- **Idempotency keys** on `applications` and `notifications` so retries never duplicate.
- **Alumni role** exists in the enum now; alumni flows are not built until after MVP.
