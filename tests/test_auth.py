import pytest

from icloud_mcp import auth
from icloud_mcp.config import config


def test_env_credentials():
    assert auth.get_credentials() == ("tester@icloud.com", "aaaa-bbbb-cccc-dddd")


def test_request_headers_are_never_consulted():
    # The header/Basic-auth credential paths were removed: nothing a caller sends
    # can switch the account the server acts on.
    assert not hasattr(auth, "_request_headers")
    assert not hasattr(auth, "_from_basic_auth")


def test_missing_credentials(monkeypatch):
    monkeypatch.setattr(config, "FALLBACK_EMAIL", None)
    monkeypatch.setattr(config, "FALLBACK_PASSWORD", None)
    with pytest.raises(auth.AuthenticationError):
        auth.get_credentials()
