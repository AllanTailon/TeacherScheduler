"""Load secrets from environment / optional .env without committing credentials."""

from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    env_path = _ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


def get_email_address() -> str:
    return os.environ.get("EMAIL_ADDRESS", "teacher.scheduler.contact@gmail.com")


def get_email_password() -> str:
    password = os.environ.get("EMAIL_PASSWORD", "").strip()
    if password:
        return password

    # Legacy fallback for local/dev containers — prefer EMAIL_PASSWORD.
    legacy = _ROOT / ".devcontainer" / "config.json"
    if legacy.exists():
        import json

        try:
            data = json.loads(legacy.read_text(encoding="utf-8"))
            legacy_pw = str(data.get("email_password", "")).strip()
            if legacy_pw and "SET_VIA" not in legacy_pw:
                return legacy_pw
        except (json.JSONDecodeError, OSError):
            pass

    raise RuntimeError(
        "EMAIL_PASSWORD não configurada. Defina a variável de ambiente "
        "ou um arquivo .env (veja .env.example)."
    )


def app_dir() -> Path:
    return Path(__file__).resolve().parent
