"""HU-2.2 Employee directory (GET /employees): smoke tests for the endpoint."""

import uuid
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeStatus

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
    assert item["start_date"] == "2026-01-15"
    # A directory row must not leak salary or email.
    assert "salary" not in item
    assert "email" not in item


def test_list_rejects_invalid_pagination(auth_client: TestClient) -> None:
    for params in ({"page": 0}, {"size": 0}, {"size": 101}, {"status": "BOGUS"}):
        assert auth_client.get("/employees", params=params).status_code == 422


# --- search, filter, pagination (task #71) ----------------------------------


def _create_many(
    client: TestClient, make_payload: PayloadFactory, tag: str, first_names: list[str]
) -> list[str]:
    """Create one employee per first name, all sharing `tag` as last name."""
    ids = []
    for first in first_names:
        response = client.post(
            "/employees", json=make_payload(first_names=first, last_names=tag)
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])
    return ids


def _search(client: TestClient, **params: Any) -> dict[str, Any]:
    response = client.get("/employees", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_search_matches_first_name_last_name_and_document(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    tag = _unique_tag()
    payload = make_employee_payload(first_names=f"Zeta{tag}", last_names=f"Omega{tag}")
    created = auth_client.post("/employees", json=payload).json()

    for term in (f"zeta{tag}", f"OMEGA{tag}", created["document_number"].lower()):
        body = _search(auth_client, q=term)
        assert [item["id"] for item in body["items"]] == [created["id"]], term


def test_search_matches_partial_text(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    tag = _unique_tag()
    created = auth_client.post(
        "/employees", json=make_employee_payload(last_names=f"Prefix{tag}suffix")
    ).json()

    body = _search(auth_client, q=tag)

    assert [item["id"] for item in body["items"]] == [created["id"]]


def test_search_requires_every_word_to_match(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    tag = _unique_tag()
    ids = _create_many(auth_client, make_employee_payload, tag, ["Ana", "Luis"])

    both = _search(auth_client, q=f"ana {tag}")
    one_missing = _search(auth_client, q=f"ana {tag} nomatchword")

    assert [item["id"] for item in both["items"]] == [ids[0]]
    assert one_missing["total"] == 0


def test_search_without_results_returns_an_empty_page(auth_client: TestClient) -> None:
    body = _search(auth_client, q=f"nobody-{_unique_tag()}")

    assert body["items"] == []
    assert body["total"] == 0


def test_search_treats_wildcards_literally(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    tag = _unique_tag()
    _create_many(auth_client, make_employee_payload, tag, ["Ana"])

    # If "%" or "_" acted as SQL wildcards these would match the employee above.
    assert _search(auth_client, q=f"{tag}%x")["total"] == 0
    assert _search(auth_client, q=f"{tag[:-1]}_")["total"] == 0


def test_blank_search_returns_everything_like_no_search(
    auth_client: TestClient,
) -> None:
    assert _search(auth_client, q="   ")["total"] == _search(auth_client)["total"]


def test_status_filter(
    auth_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    tag = _unique_tag()
    ids = _create_many(auth_client, make_employee_payload, tag, ["Ana", "Luis"])
    employee = db.get(Employee, uuid.UUID(ids[1]))
    assert employee is not None
    employee.status = EmployeeStatus.INACTIVO
    db.commit()  # only releases the SAVEPOINT (see the `db` fixture)

    everyone = _search(auth_client, q=tag)
    active = _search(auth_client, q=tag, status="ACTIVO")
    inactive = _search(auth_client, q=tag, status="INACTIVO")

    assert everyone["total"] == 2
    assert [item["id"] for item in active["items"]] == [ids[0]]
    assert [item["id"] for item in inactive["items"]] == [ids[1]]


def test_pagination_splits_results_without_repeating_rows(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    tag = _unique_tag()
    ids = _create_many(
        auth_client,
        make_employee_payload,
        tag,
        ["Ana", "Beto", "Carla", "Diego", "Eva"],
    )

    pages = [_search(auth_client, q=tag, size=2, page=page) for page in (1, 2, 3)]

    assert [len(page["items"]) for page in pages] == [2, 2, 1]
    assert all(page["total"] == 5 for page in pages)
    assert [page["page"] for page in pages] == [1, 2, 3]
    seen = [item["id"] for page in pages for item in page["items"]]
    assert seen == ids  # same last name, so ordered by first name: Ana..Eva


def test_page_beyond_the_end_is_empty_but_keeps_the_total(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    tag = _unique_tag()
    _create_many(auth_client, make_employee_payload, tag, ["Ana", "Beto"])

    body = _search(auth_client, q=tag, size=2, page=9)

    assert body["items"] == []
    assert body["total"] == 2


def test_results_are_ordered_by_last_then_first_name(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    tag = _unique_tag()
    # The search finds all three by `tag`; the last names differ only after it.
    created = []
    for first, last in (("Zoe", f"{tag}b"), ("Ana", f"{tag}b"), ("Mia", f"{tag}a")):
        response = auth_client.post(
            "/employees", json=make_employee_payload(first_names=first, last_names=last)
        )
        created.append((first, response.json()["id"]))
    by_name = dict(created)

    body = _search(auth_client, q=tag)

    assert [item["id"] for item in body["items"]] == [
        by_name["Mia"],  # last name ...a
        by_name["Ana"],  # last name ...b, first name Ana
        by_name["Zoe"],  # last name ...b, first name Zoe
    ]
