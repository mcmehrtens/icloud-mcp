"""Credential resolution for the iCloud MCP server.

Credentials come only from the environment (``ICLOUD_EMAIL`` /
``ICLOUD_APP_SPECIFIC_PASSWORD``). Request headers are never consulted, so a
caller cannot point the server at a different account or learn which one it uses.
"""

import logging

from .config import config

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when no usable iCloud credentials are available."""


def get_credentials() -> tuple[str, str]:
    """Return ``(email, app_specific_password)`` from the environment."""
    email = config.FALLBACK_EMAIL
    password = config.FALLBACK_PASSWORD
    if not email or not password:
        raise AuthenticationError(
            "iCloud credentials are missing. Set ICLOUD_EMAIL and ICLOUD_APP_SPECIFIC_PASSWORD "
            "(an app-specific password from https://account.apple.com/account/manage, "
            "not the Apple ID password)."
        )
    return email.strip(), password.strip().replace(" ", "")


def require_auth() -> tuple[str, str]:
    """Alias kept for readability at call sites."""
    return get_credentials()


def redact_secrets(text: str) -> str:
    """Remove the configured password from a message before it leaves the server."""
    try:
        _, password = get_credentials()
    except Exception:
        return text
    if password and password in text:
        text = text.replace(password, "***")
    return text
