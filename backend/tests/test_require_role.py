"""require_role dependency, exercised on a throwaway app (not on real routes)."""

from collections.abc import Iterator
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from tests.conftest import TEST_PASSWORD, make_user

FORBIDDEN = "You do not have permission to perform this action"


@pytest.fixture
def role_client(db: Session) -> Iterator[TestClient]:
    """A tiny app with the real login plus two routes guarded by require_role."""
    mini_app = FastAPI()
    mini_app.include_router(auth_router)

    @mini_app.get("/only-admin")
    def only_admin(
        user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    ) -> dict[str, str]:
        return {"role": user.role.value}

    @mini_app.get("/admin-or-hr")
    def admin_or_hr(
        user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.HR))],
    ) -> dict[str, str]:
        return {"role": user.role.value}

    def _override_get_db() -> Iterator[Session]:
        yield db

    mini_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(mini_app) as client:
        yield client


def _login_as(
    client: TestClient, db: Session, password_hash: str, role: UserRole
) -> None:
    user = make_user(db, password_hash, role)
    response = client.post(
        "/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text


def test_without_session_returns_401(role_client: TestClient) -> None:
    assert role_client.get("/only-admin").status_code == 401


def test_allowed_role_gets_through(
    role_client: TestClient, db: Session, password_hash: str
) -> None:
    _login_as(role_client, db, password_hash, UserRole.ADMIN)

    response = role_client.get("/only-admin")

    assert response.status_code == 200
    assert response.json() == {"role": "ADMIN"}


@pytest.mark.parametrize("role", [UserRole.HR, UserRole.MANAGER, UserRole.EMPLOYEE])
def test_other_roles_get_403_on_an_admin_only_route(
    role_client: TestClient, db: Session, password_hash: str, role: UserRole
) -> None:
    _login_as(role_client, db, password_hash, role)

    response = role_client.get("/only-admin")

    assert response.status_code == 403
    assert response.json()["detail"] == FORBIDDEN


def test_several_roles_can_be_allowed(
    role_client: TestClient, db: Session, password_hash: str
) -> None:
    _login_as(role_client, db, password_hash, UserRole.HR)

    assert role_client.get("/admin-or-hr").status_code == 200


def test_403_does_not_reveal_which_roles_are_accepted(
    role_client: TestClient, db: Session, password_hash: str
) -> None:
    _login_as(role_client, db, password_hash, UserRole.EMPLOYEE)

    detail = role_client.get("/only-admin").json()["detail"]

    assert "ADMIN" not in detail
