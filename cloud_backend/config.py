import os


ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
MAX_QUERIES_PER_DEBUG: int = int(os.getenv("MAX_QUERIES_PER_DEBUG", "15"))
MAX_LLM_CALLS_PER_DEBUG: int = int(os.getenv("MAX_LLM_CALLS_PER_DEBUG", "20"))
ALLOWED_ORIGINS: list[str] = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
