"""Load secrets from environment / .env / Streamlit secrets without committing credentials."""

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
        # Fill missing or blank env vars (Compose often injects EMAIL_PASSWORD=).
        if not str(os.environ.get(key, "")).strip():
            os.environ[key] = value


_load_dotenv()


def _from_streamlit_secrets(key: str) -> str:
    """Read Streamlit Cloud / local secrets.toml when available."""
    try:
        import streamlit as st

        secrets = st.secrets
    except Exception:
        return ""

    try:
        value = secrets.get(key)
    except Exception:
        return ""

    if value is None:
        return ""
    return str(value).strip()


def get_email_address() -> str:
    return (
        os.environ.get("EMAIL_ADDRESS", "").strip()
        or _from_streamlit_secrets("EMAIL_ADDRESS")
        or "teacher.scheduler.contact@gmail.com"
    )


def get_email_password() -> str:
    password = os.environ.get("EMAIL_PASSWORD", "").strip() or _from_streamlit_secrets(
        "EMAIL_PASSWORD"
    )
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
        "EMAIL_PASSWORD não configurada. Defina a variável de ambiente, "
        "um arquivo .env, ou Streamlit Secrets "
        "(Settings → Secrets: EMAIL_PASSWORD = \"...\")."
    )


def app_dir() -> Path:
    return Path(__file__).resolve().parent
