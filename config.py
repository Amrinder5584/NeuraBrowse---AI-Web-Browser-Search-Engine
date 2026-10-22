"""Application configuration. Every value can be overridden with an environment variable."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _flag(name, default="1"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # --- storage -----------------------------------------------------------
    DATABASE = os.environ.get(
        "DATABASE_PATH", os.path.join(os.path.dirname(BASE_DIR), "data", "browser.db")
    )

    # --- security ----------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # --- AI ----------------------------------------------------------------
    # Without ANTHROPIC_API_KEY the app runs in "offline" mode (extractive answers).
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or None
    AI_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-5-5")
    AI_MAX_TOKENS = int(os.environ.get("AI_MAX_TOKENS", "700"))

    # --- search providers ---------------------------------------------------
    ENABLE_WIKIPEDIA = _flag("ENABLE_WIKIPEDIA", "1")
    BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY") or None
    MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "10"))

    # --- networking ---------------------------------------------------------
    REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "8"))
    MAX_PAGE_BYTES = 1_000_000
    PAGE_CACHE_SECONDS = 3600
    USER_AGENT = "NeuraBrowse/1.0 (college mini project)"
