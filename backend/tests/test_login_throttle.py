"""Login brute-force limits, client IP resolution and server-side logging."""

import logging
from types import SimpleNamespace

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app import main
from app.core import network
from app.core.rate_limit import FailureCounter, LoginThrottle
from app.models.user import User
from tests.conftest import TEST_PASSWORD

UNKNOWN_EMAIL = "nobody@tat-test.example.com"


def _attempt(client: TestClient, email: str, password: str = "wrong-password"):
    return client.post("/auth/login", json={"email": email, "password": password})


def _block(client: TestClient, email: str) -> None:
    for _ in range(5):
        assert _attempt(client, email).status_code == 401


def test_fifth_failure_blocks_the_next_attempt(
    client: TestClient, hr_user: User
) -> None:
    _block(client, hr_user.email)

    response = _attempt(client, hr_user.email)

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_correct_password_is_also_blocked_during_the_lockout(
    client: TestClient, hr_user: User
) -> None:
    _block(client, hr_user.email)
    assert _attempt(client, hr_user.email, TEST_PASSWORD).status_code == 429


def test_success_resets_the_account_counter(client: TestClient, hr_user: User) -> None:
    for _ in range(4):
        _attempt(client, hr_user.email)
    assert _attempt(client, hr_user.email, TEST_PASSWORD).status_code == 200
    for _ in range(4):
        assert _attempt(client, hr_user.email).status_code == 401


def test_unknown_email_is_throttled_like_a_real_one(client: TestClient) -> None:
    # A different outcome would reveal which emails exist.
    _block(client, UNKNOWN_EMAIL)
    assert _attempt(client, UNKNOWN_EMAIL).status_code == 429


def test_blocking_one_email_does_not_block_another(
    client: TestClient, hr_user: User
) -> None:
    _block(client, UNKNOWN_EMAIL)
    assert _attempt(client, hr_user.email, TEST_PASSWORD).status_code == 200


def test_email_case_cannot_dodge_the_limit(client: TestClient, hr_user: User) -> None:
    _block(client, hr_user.email)
    assert _attempt(client, hr_user.email.upper()).status_code == 429


def test_lockout_expires_with_the_window() -> None:
    now = [1000.0]
    counter = FailureCounter(2, 60, clock=lambda: now[0])
    counter.record_failure("k")
    counter.record_failure("k")
    assert counter.retry_after("k") == 60

    now[0] += 59
    assert counter.retry_after("k") == 1

    now[0] += 1
    assert counter.retry_after("k") == 0


def test_ip_limit_stops_spraying_across_accounts() -> None:
    throttle = LoginThrottle(account_failures=100, ip_failures=3, window_seconds=60)
    for i in range(3):
        throttle.record_failure("1.2.3.4", f"user{i}@example.com")

    assert throttle.retry_after("1.2.3.4", "other@example.com") > 0
    assert throttle.retry_after("5.6.7.8", "other@example.com") == 0


def test_success_does_not_erase_the_ip_counter() -> None:
    throttle = LoginThrottle(account_failures=100, ip_failures=2, window_seconds=60)
    throttle.record_failure("1.2.3.4", "a@example.com")
    throttle.record_failure("1.2.3.4", "b@example.com")

    throttle.record_success("1.2.3.4", "a@example.com")

    assert throttle.retry_after("1.2.3.4", "c@example.com") > 0


def test_tracked_keys_are_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(FailureCounter, "MAX_KEYS", 10)
    counter = FailureCounter(1, 60, clock=lambda: 0.0)
    for i in range(100):
        counter.record_failure(f"k{i}")
    assert len(counter._failures) <= 10


def test_failed_login_logs_neither_password_nor_email(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="tat.auth"):
        _attempt(client, UNKNOWN_EMAIL, "super-secret-typed-password")

    assert "login failed" in caplog.text
    assert "super-secret-typed-password" not in caplog.text
    assert UNKNOWN_EMAIL not in caplog.text


# --- client IP -------------------------------------------------------------


def _request(forwarded: str | None, peer: str = "10.0.0.1") -> Request:
    headers = []
    if forwarded is not None:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return Request(
        {"type": "http", "headers": headers, "client": (peer, 1234)},
    )


def _with_hops(monkeypatch: pytest.MonkeyPatch, hops: int) -> None:
    monkeypatch.setattr(
        network, "get_settings", lambda: SimpleNamespace(trusted_proxy_hops=hops)
    )


def test_without_proxies_the_forwarded_header_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _with_hops(monkeypatch, 0)
    assert network.client_ip(_request("6.6.6.6")) == "10.0.0.1"


def test_spoofed_entries_on_the_left_are_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _with_hops(monkeypatch, 1)
    # The client invented 6.6.6.6; our proxy appended the address it really saw.
    assert network.client_ip(_request("6.6.6.6, 200.1.1.1")) == "200.1.1.1"


def test_two_proxies_read_the_second_entry_from_the_right(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _with_hops(monkeypatch, 2)
    assert network.client_ip(_request("6.6.6.6, 200.1.1.1, 76.0.0.1")) == "200.1.1.1"


@pytest.mark.parametrize("forwarded", [None, "not-an-ip", "evil\ninjected"])
def test_missing_or_invalid_header_falls_back_to_the_peer(
    monkeypatch: pytest.MonkeyPatch, forwarded: str | None
) -> None:
    _with_hops(monkeypatch, 1)
    assert network.client_ip(_request(forwarded)) == "10.0.0.1"


# --- unexpected errors -----------------------------------------------------


def test_unhandled_error_is_logged_but_not_revealed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = main.create_app()

    def boom() -> None:
        raise RuntimeError("internal detail: connection string")

    app.add_api_route("/boom", boom)
    client = TestClient(app, raise_server_exceptions=False)

    with caplog.at_level(logging.ERROR, logger="tat"):
        response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "internal detail" in caplog.text
