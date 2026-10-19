"""Checks the test setup itself: isolation and the safety rules."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from tests.conftest import TEST_PASSWORD

LEFTOVER_MARKER = "@tat-test.example.com"


def _count_test_users(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.email.like(f"%{LEFTOVER_MARKER}"))
        )
        or 0
    )


def test_health_endpoint_uses_the_test_session(client: TestClient) -> None:
    response = client.get("/health/db")
    assert response.status_code == 200


def test_data_is_visible_inside_the_test(db: Session, hr_user: User) -> None:
    assert _count_test_users(db) >= 1


def test_commit_in_the_app_does_not_persist_across_tests(
    client: TestClient, hr_user: User
) -> None:
    # The logout endpoint commits (token_version += 1). It must stay inside the
    # test's transaction.
    client.post("/auth/login", json={"email": hr_user.email, "password": TEST_PASSWORD})
    assert client.post("/auth/logout").status_code == 204


def test_no_rows_survive_between_tests(db: Session) -> None:
    # Runs after the tests above: nothing they created may still exist.
    assert _count_test_users(db) == 0
