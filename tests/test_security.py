import asyncio
import io

import pytest


def test_model_config_never_returns_raw_key():
    from src.config.settings import ProviderConfig

    result = ProviderConfig(api_key="sk-test-secret-123456").to_dict()
    assert "api_key" not in result
    assert result["api_key_set"] is True
    assert "sk-test-secret-123456" not in str(result)
    assert result["api_key_masked"].startswith("sk-t")


def test_streamed_upload_is_hard_limited(tmp_path):
    from src.core.dedup import FileDeduplicator, UploadTooLargeError

    dedup = FileDeduplicator(str(tmp_path))
    with pytest.raises(UploadTooLargeError):
        asyncio.run(dedup.process_upload(io.BytesIO(b"12345"), "clip.mp4", max_bytes=4))
    assert not list(tmp_path.iterdir())


def test_signed_session_and_csrf(monkeypatch):
    import src.security as security

    monkeypatch.setattr(security, "AUTH_ENABLED", True)
    monkeypatch.setattr(security, "SESSION_SECRET", "test-session-secret")
    session = security.create_session()
    assert security.validate_session(session)
    assert not security.validate_session(session + "x")

    csrf = security.new_csrf_token()
    assert security.valid_csrf(csrf, csrf)
    assert not security.valid_csrf(csrf, "wrong")


def test_auth_cookie_defaults_to_non_secure_for_local_http(monkeypatch):
    from starlette.responses import Response
    import src.security as security

    monkeypatch.delenv("VIDEONOTE_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("VIDEONOTE_DOMAIN", raising=False)
    response = Response()
    security.set_auth_cookies(response, "session", "csrf")
    assert "Secure" not in response.headers["set-cookie"]
