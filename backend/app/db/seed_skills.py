# Import skills.csv into the skills table (idempotent).
# Usage: python -m app.db.seed_skills  (from backend/)
import csv
import pathlib
from sqlalchemy import select
from app.db.db import get_session_factory, init_db
from app.db.models import Skill

CSV_PATH = pathlib.Path(__file__).resolve().parents[2].parent / "skills.csv"
# fallback when running from different cwd
if not CSV_PATH.exists():
    CSV_PATH = pathlib.Path("skills.csv")
if not CSV_PATH.exists():
    CSV_PATH = pathlib.Path(__file__).resolve().parents[2] / "skills.csv"
if not CSV_PATH.exists():
    CSV_PATH = pathlib.Path.cwd() / "skills.csv"

# normalize category -> enum-like value
def norm_category(raw: str) -> str:
    return raw.strip().upper().replace(" ", "_").replace("&", "").replace("__", "_").strip("_") or "OTHER"

def seed_skills() -> int:
    init_db()
    session = get_session_factory()()
    try:
        if not CSV_PATH.exists():
            print(f"skills.csv not found at {CSV_PATH}")
            return 0
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            inserted = 0
            skipped = 0
            for row in reader:
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                # skip if exists (case-sensitive unique on name)
                if session.scalar(select(Skill).where(Skill.name == name)):
                    skipped += 1
                    continue
                cat = norm_category(row.get("category") or "OTHER")
                aliases = (row.get("aliases") or "").strip()
                desc = f"aliases: {aliases}" if aliases else None
                session.add(Skill(name=name, category=cat, description=desc))
                inserted += 1
            session.commit()
            print(f"skills seeded: inserted={inserted} skipped(existing)={skipped}")
            return inserted
    finally:
        session.close()

if __name__ == "__main__":
    seed_skills()
