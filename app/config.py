import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


@dataclass
class Settings:
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "4000"))

    # LLM Settings
    # Supported providers: "groq", "gemini", "openai", "anthropic", "mock"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()

    # Groq (Primary LLM Provider)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    
    # Gemini (Google)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-6-luna")

    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

    # Network / Fetching limits
    REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15.0"))
    MAX_CONTENT_LENGTH_BYTES: int = int(os.getenv("MAX_CONTENT_LENGTH_BYTES", str(5 * 1024 * 1024)))  # 5 MB
    MAX_REDIRECTS: int = int(os.getenv("MAX_REDIRECTS", "5"))
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (LinkAnalysisBot/1.0)"
    )


settings = Settings()
