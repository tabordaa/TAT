"""HU-2.2 Employee directory (GET /employees): smoke tests for the endpoint."""

import uuid
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

PayloadFactory = Callable[..., dict[str, Any]]


def _unique_tag() -> str:
    """A letters-only word, so a search for it can only match rows of this test."""
    return "".join(chr(ord("a") + int(c, 16) % 26) for c in uuid.uuid4().hex[:12])


def test_list_requires_a_session(client: TestClient) -> None:
    assert client.get("/employees").status_code == 401


def test_list_returns_page_metadata_and_no_sensitive_fields(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    tag = _unique_tag()
    created = auth_client.post("/employees", json=make_employee_payload(last_names=tag))
    assert created.status_code == 201

    response = auth_client.get("/employees", params={"q": tag})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert (body["page"], body["size"]) == (1, 20)
    item = body["items"][0]
    assert item["id"] == created.json()["id"]
    assert item["status"] == "ACTIVO"
    # A directory row must not leak salary or email.
    assert "salary" not in item
    assert "email" not in item


def test_list_rejects_invalid_pagination(auth_client: TestClient) -> None:
    for params in ({"page": 0}, {"size": 0}, {"size": 101}, {"status": "BOGUS"}):
        assert auth_client.get("/employees", params=params).status_code == 422
