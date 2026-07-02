from pathlib import Path

from dotenv import load_dotenv

from app.utils.env import require_env


load_dotenv()


class Settings:
    """Application configuration loaded from environment variables."""

    OPENAI_API_KEY: str
    OPENAI_VECTOR_STORE_ID: str
    OPENAI_ASSISTANT_ID: str
    OPTISIGNS_BASE_URL: str
    MARKDOWN_DIR: Path
    STATE_FILE: Path
    LOG_FILE: Path

    def __init__(self) -> None:
        self.OPENAI_API_KEY = require_env("OPENAI_API_KEY")
        self.OPENAI_VECTOR_STORE_ID = require_env("OPENAI_VECTOR_STORE_ID")
        self.OPENAI_ASSISTANT_ID = require_env("OPENAI_ASSISTANT_ID")
        self.OPTISIGNS_BASE_URL = require_env("OPTISIGNS_BASE_URL")
        self.MARKDOWN_DIR = Path(require_env("MARKDOWN_DIR"))
        self.STATE_FILE = Path(require_env("STATE_FILE"))
        self.LOG_FILE = Path(require_env("LOG_FILE"))
