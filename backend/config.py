import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _read_api_key() -> str:
    # CHAT_EINFRA_KEY_FILE (e.g. a Docker secret under /run/secrets/) wins over
    # the plain variable, so a stale key left in .env cannot shadow it. A set
    # but missing file is a startup error rather than a silent fallback.
    key_file = os.getenv("CHAT_EINFRA_KEY_FILE")
    if key_file:
        with open(key_file, encoding="utf-8") as f:
            return f.read().strip()
    return os.getenv("CHAT_EINFRA_KEY", os.getenv("VLLM_API_KEY", ""))


class Settings:
    CHAT_EINFRA_URL: str = os.getenv(
        "CHAT_EINFRA_URL",
        os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1"),
    )
    CHAT_EINFRA_KEY: str = _read_api_key()
    APP_PASSWORD: str = os.getenv("APP_PASSWORD", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET") or secrets.token_hex(32)
    MODEL_NAME: str = os.getenv("MODEL_NAME", "local-model")
    DB_PATH: str = os.getenv("DB_PATH", "jailbreaking.db")

    def validate(self):
        if not self.APP_PASSWORD:
            raise RuntimeError("APP_PASSWORD must be set")
        if not self.CHAT_EINFRA_URL:
            raise RuntimeError("CHAT_EINFRA_URL must be set")


settings = Settings()
