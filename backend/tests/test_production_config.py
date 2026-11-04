"""Production hardening: secure cookie at startup, closed docs, cache headers."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app import main
from app.core.config import Settings

JWT_SECRET = SecretStr("x" * 32)
DATABASE_URL = SecretStr("postgresql+psycopg://user:pass@localhost:5432/none")


def _settings(environment: str, cookie_secure: bool) -> Settings:
    return Settings(
        _env_file=None,
        environment=environment,
        cookie_secure=cookie_secure,
        database_url=DATABASE_URL,
        jwt_secret_key=JWT_SECRET,
    )


def test_production_without_secure_cookie_refuses_to_start() -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        _settings("production", cookie_secure=False)


def test_production_with_secure_cookie_starts() -> None:
    assert _settings("production", cookie_secure=True).cookie_secure is True


def test_development_allows_plain_http_cookie() -> None:
    assert _settings("development", cookie_secure=False).cookie_secure is False


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_are_closed_in_production(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setattr(
        main, "get_settings", lambda: _settings("production", cookie_secure=True)
    )
    client = TestClient(main.create_app())
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_stay_open_in_development(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setattr(
        main, "get_settings", lambda: _settings("development", cookie_secure=False)
    )
    client = TestClient(main.create_app())
    assert client.get(path).status_code == 200


def test_every_response_forbids_caching(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_error_responses_forbid_caching_too(client: TestClient) -> None:
    response = client.get("/employees")
    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "no-store"
