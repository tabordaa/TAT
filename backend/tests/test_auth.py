"""HU-1.1 Login and HU-1.3 Logout (plus the current-session endpoint)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.conftest import TEST_PASSWORD, cookie_name, make_user

INVALID_CREDENTIALS = "Invalid email or password"


def _login(client: TestClient, email: str, password: str = TEST_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


# --- login -----------------------------------------------------------------


def test_login_succeeds_and_returns_public_user(
    client: TestClient, hr_user: User
) -> None:
    response = _login(client, hr_user.email)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == hr_user.email
    assert body["role"] == "HR"
    # The response must never expose the password hash.
    assert "hashed_password" not in body
    assert "password" not in body


def test_login_sets_httponly_samesite_cookie(client: TestClient, hr_user: User) -> None:
    response = _login(client, hr_user.email)

    set_cookie = response.headers["set-cookie"].lower()
    assert set_cookie.startswith(f"{cookie_name()}=")
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/" in set_cookie


def test_login_email_is_case_insensitive(client: TestClient, hr_user: User) -> None:
    assert _login(client, hr_user.email.upper()).status_code == 200


def test_login_with_wrong_password_returns_401(
    client: TestClient, hr_user: User
) -> None:
    response = _login(client, hr_user.email, "not-the-password")

    assert response.status_code == 401
    assert response.json()["detail"] == INVALID_CREDENTIALS
    assert cookie_name() not in response.cookies


def test_login_unknown_email_gives_same_error_as_wrong_password(
    client: TestClient, hr_user: User
) -> None:
    # No user enumeration: both failures must be indistinguishable.
    wrong_password = _login(client, hr_user.email, "not-the-password")
    unknown_email = _login(client, "nobody-at-all@tat-test.example.com")

    assert unknown_email.status_code == wrong_password.status_code == 401
    assert unknown_email.json() == wrong_password.json()


def test_login_inactive_user_returns_same_401(
    client: TestClient, db: Session, password_hash: str
) -> None:
    inactive = make_user(db, password_hash, is_active=False)

    response = _login(client, inactive.email)

    assert response.status_code == 401
    assert response.json()["detail"] == INVALID_CREDENTIALS


def test_login_rejects_malformed_body(client: TestClient) -> None:
    assert (
        client.post(
            "/auth/login", json={"email": "not-an-email", "password": "x"}
        ).status_code
        == 422
    )
    assert (
        client.post("/auth/login", json={"email": "a@b.co", "password": ""}).status_code
        == 422
    )


# --- current session -------------------------------------------------------


def test_me_without_session_returns_401(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_with_session_returns_the_user(
    auth_client: TestClient, hr_user: User
) -> None:
    response = auth_client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == hr_user.email


def test_me_with_tampered_cookie_returns_401(client: TestClient) -> None:
    client.cookies.set(cookie_name(), "this.is.not-a-valid-jwt")

    assert client.get("/auth/me").status_code == 401


# --- logout ----------------------------------------------------------------


def test_logout_returns_204_and_clears_the_cookie(auth_client: TestClient) -> None:
    response = auth_client.post("/auth/logout")

    assert response.status_code == 204
    # delete_cookie sends the same cookie name with an expired date / max-age=0.
    set_cookie = response.headers["set-cookie"].lower()
    assert set_cookie.startswith(f"{cookie_name()}=")
    assert "max-age=0" in set_cookie or "expires=" in set_cookie
    assert auth_client.get("/auth/me").status_code == 401


def test_logout_revokes_the_previous_token(
    client: TestClient, hr_user: User, db: Session
) -> None:
    login = _login(client, hr_user.email)
    old_token = login.cookies[cookie_name()]
    version_before = hr_user.token_version

    assert client.post("/auth/logout").status_code == 204

    db.refresh(hr_user)
    assert hr_user.token_version == version_before + 1
    # Replaying the old, still-unexpired token must fail: it is revoked.
    client.cookies.set(cookie_name(), old_token)
    assert client.get("/auth/me").status_code == 401


def test_logout_without_session_is_idempotent(client: TestClient) -> None:
    assert client.post("/auth/logout").status_code == 204


def test_user_can_log_in_again_after_logout(client: TestClient, hr_user: User) -> None:
    _login(client, hr_user.email)
    client.post("/auth/logout")

    assert _login(client, hr_user.email).status_code == 200
    assert client.get("/auth/me").status_code == 200
