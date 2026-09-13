# Core config — values come from the environment (.env).

import os

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    PROJECT_NAME: str = "AI Placement Assistant"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/placepilot")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    WEAVIATE_URL: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    WEAVIATE_GRPC_PORT: int = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174")

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_REASONING_MODEL: str = os.getenv("GROQ_REASONING_MODEL", "openai/gpt-oss-120b")
    GROQ_LIGHT_MODEL: str = os.getenv("GROQ_LIGHT_MODEL", "openai/gpt-oss-20b")
    GROQ_TIMEOUT: float = float(os.getenv("GROQ_TIMEOUT", "30"))

    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    # --- MCP servers ---
    MCP_HOST: str = os.getenv("MCP_HOST", "127.0.0.1")
    MCP_PLACEMENT_PORT: int = int(os.getenv("MCP_PLACEMENT_PORT", "8101"))
    MCP_STUDENT_PORT: int = int(os.getenv("MCP_STUDENT_PORT", "8102"))
    MCP_KNOWLEDGE_PORT: int = int(os.getenv("MCP_KNOWLEDGE_PORT", "8103"))
    # Client-side URLs (default to the same host the servers bind to).
    MCP_PLACEMENT_URL: str = os.getenv("MCP_PLACEMENT_URL", "")
    MCP_STUDENT_URL: str = os.getenv("MCP_STUDENT_URL", "")
    MCP_KNOWLEDGE_URL: str = os.getenv("MCP_KNOWLEDGE_URL", "")
    # Agent -> MCP call policy
    MCP_TOOL_TIMEOUT_S: float = float(os.getenv("MCP_TOOL_TIMEOUT_S", "20"))
    MCP_TOOL_RETRIES: int = int(os.getenv("MCP_TOOL_RETRIES", "1"))
    MCP_CATALOG_TTL_S: float = float(os.getenv("MCP_CATALOG_TTL_S", "300"))

    # --- RAG / retrieval ---
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "120"))
    HYBRID_ALPHA: float = float(os.getenv("HYBRID_ALPHA", "0.65"))
    RETRIEVAL_MIN_SCORE_HYBRID: float = float(os.getenv("RETRIEVAL_MIN_SCORE_HYBRID", "0.70"))
    RETRIEVAL_MIN_SCORE_VECTOR: float = float(os.getenv("RETRIEVAL_MIN_SCORE_VECTOR", "0.30"))
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))  # 10 MB
    ALLOWED_DOC_TYPES: tuple[str, ...] = tuple(
        t.strip().lower() for t in os.getenv("ALLOWED_DOC_TYPES", ".pdf,.txt,.md").split(",") if t.strip()
    )

    # --- Rate limiting (per-user, in-memory sliding window) ---
    AI_CHAT_RATE_LIMIT: int = int(os.getenv("AI_CHAT_RATE_LIMIT", "20"))
    AI_CHAT_RATE_WINDOW_S: int = int(os.getenv("AI_CHAT_RATE_WINDOW_S", "60"))

    # --- Observability ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def mcp_server_urls(self) -> dict[str, dict]:
        """Client-side MCP server config; explicit URLs win over host/port defaults."""
        defaults = {
            "placement": f"http://{self.MCP_HOST}:{self.MCP_PLACEMENT_PORT}/mcp",
            "student": f"http://{self.MCP_HOST}:{self.MCP_STUDENT_PORT}/mcp",
            "knowledge": f"http://{self.MCP_HOST}:{self.MCP_KNOWLEDGE_PORT}/mcp",
        }
        explicit = {
            "placement": self.MCP_PLACEMENT_URL,
            "student": self.MCP_STUDENT_URL,
            "knowledge": self.MCP_KNOWLEDGE_URL,
        }
        return {
            key: {"url": explicit[key] or defaults[key], "transport": "streamable_http"}
            for key in defaults
        }

    def validate_secrets(self) -> list[str]:
        """Return a list of fatal misconfigurations (empty = ok).
        Production deployments must not run on default/empty secrets."""
        problems: list[str] = []
        if self.JWT_SECRET in ("", "change-me"):
            problems.append("JWT_SECRET is not set (refusing to run on the default value)")
        if not self.GROQ_API_KEY and os.getenv("PLACEPILOT_REQUIRE_GROQ", "0") in ("1", "true"):
            problems.append("GROQ_API_KEY is not set")
        return problems


settings = Settings()
