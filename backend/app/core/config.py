# Core config — Phase 0 skeleton. Values come from environment (.env).

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "AI Placement Assistant"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg://placepilot:placepilot@localhost:5432/placepilot")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    WEAVIATE_URL: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_REASONING_MODEL: str = os.getenv("GROQ_REASONING_MODEL", "openai/gpt-oss-120b")
    GROQ_LIGHT_MODEL: str = os.getenv("GROQ_LIGHT_MODEL", "openai/gpt-oss-20b")
    GROQ_TIMEOUT: float = float(os.getenv("GROQ_TIMEOUT", "30"))

    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


settings = Settings()
