"""HU-2.7 Personal data: contact fields and a private profile photo."""

import logging
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.me import provide_storage
from app.main import app
from app.models.audit_log import AuditAction, AuditLog
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.services.photo_storage import (
    MAX_PHOTO_BYTES,
    StorageError,
    SupabasePhotoStorage,
    detect_image,
)
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]

PNG = b"\x89PNG\r\n\x1a\n" + b"png-body"
JPEG = b"\xff\xd8\xff\xe0" + b"jpeg-body"
WEBP = b"RIFF\x10\x00\x00\x00WEBP" + b"webp-body"
SECRET_KEY = "service-role-key-that-must-not-leak"


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_with: StorageError | None = None
        self.fail_delete = False

    def upload(self, path: str, content: bytes, content_type: str) -> None:
        if self.fail_with:
            raise self.fail_with
        self.objects[path] = content

    def download(self, path: str) -> bytes:
        if self.fail_with:
            raise self.fail_with
        return self.objects[path]

    def delete(self, path: str) -> None:
        if self.fail_delete:
            raise StorageError("delete failed")
        del self.objects[path]


@pytest.fixture
def storage(client: TestClient) -> Iterator[FakeStorage]:
    fake = FakeStorage()
    app.dependency_overrides[provide_storage] = lambda: fake
    yield fake  # the `client` fixture clears the override afterwards


def _login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    response = client.post(
        "/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text


@pytest.fixture
def records(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> list[dict[str, Any]]:
    return [
        auth_client.post("/employees", json=make_employee_payload()).json()
        for _ in range(2)
    ]


@pytest.fixture
def user(db: Session, password_hash: str, records: list[dict[str, Any]]) -> User:
    linked = make_user(db, password_hash, UserRole.EMPLOYEE)
    linked.employee_id = uuid.UUID(records[0]["id"])
    db.commit()
    return linked


@pytest.fixture
def me(client: TestClient, user: User) -> TestClient:
    _login(client, user)
    return client


def _upload(client: TestClient, content: bytes, name: str = "a.png", kind: str = "image/png"):
    return client.put("/me/employee/photo", files={"photo": (name, content, kind)})


# --- CA01: only contact fields -------------------------------------------------


def test_employee_updates_phone_and_address(me: TestClient) -> None:
    response = me.patch(
        "/me/employee", json={"phone": "+57 300 123 4567", "address": "Calle 10 # 20-30"}
    )
    assert response.status_code == 200
    assert response.json()["phone"] == "+57 300 123 4567"
    assert response.json()["address"] == "Calle 10 # 20-30"


@pytest.mark.parametrize(
    "field",
    [
        "salary",
        "position",
        "area",
        "status",
        "email",
        "document_number",
        "first_names",
        "contract_type",
        "start_date",
        "end_date",
        "photo_path",
        "id",
    ],
)
def test_any_other_field_is_rejected(me: TestClient, field: str) -> None:
    response = me.patch("/me/employee", json={"phone": "3001234567", field: "x"})
    assert response.status_code == 422


def test_rejected_request_changes_nothing(
    me: TestClient, db: Session, records: list[dict[str, Any]]
) -> None:
    me.patch("/me/employee", json={"phone": "3001234567", "salary": "999"})
    employee = db.get(Employee, uuid.UUID(records[0]["id"]))
    assert employee is not None
    assert employee.phone is None
    assert str(employee.salary) == records[0]["salary"]


@pytest.mark.parametrize("phone", ["abc", "123", "+57 300<script>", "1" * 31])
def test_invalid_phone_is_rejected(me: TestClient, phone: str) -> None:
    assert me.patch("/me/employee", json={"phone": phone}).status_code == 422


def test_address_has_a_limit(me: TestClient) -> None:
    assert me.patch("/me/employee", json={"address": "x" * 201}).status_code == 422


def test_omitted_field_stays_and_null_clears(me: TestClient) -> None:
    me.patch("/me/employee", json={"phone": "3001234567", "address": "Calle 1"})

    only_address = me.patch("/me/employee", json={"address": "Calle 2"}).json()
    assert only_address["phone"] == "3001234567"

    cleared = me.patch("/me/employee", json={"phone": None}).json()
    assert cleared["phone"] is None
    assert cleared["address"] == "Calle 2"


def test_requires_a_session(client: TestClient) -> None:
    assert client.patch("/me/employee", json={}).status_code == 401
    assert client.get("/me/employee/photo").status_code == 401
    assert _upload(client, PNG).status_code == 401


def test_account_without_a_record_gets_404(
    client: TestClient, db: Session, password_hash: str
) -> None:
    _login(client, make_user(db, password_hash, UserRole.EMPLOYEE))
    assert client.patch("/me/employee", json={"phone": "3001234567"}).status_code == 404


# --- CA02: reflected at once in the shared record ------------------------------


def test_hr_sees_the_change_immediately(
    client: TestClient, db: Session, password_hash: str, user: User, records: list[dict[str, Any]]
) -> None:
    _login(client, user)
    client.patch("/me/employee", json={"address": "Calle Nueva 5"})

    _login(client, make_user(db, password_hash, UserRole.HR))
    detail = client.get(f"/employees/{records[0]['id']}").json()
    assert detail["address"] == "Calle Nueva 5"


# --- audit ---------------------------------------------------------------------


def test_contact_change_is_audited_with_only_what_changed(
    me: TestClient, db: Session, user: User, records: list[dict[str, Any]]
) -> None:
    me.patch("/me/employee", json={"phone": "3001234567"})
    me.patch("/me/employee", json={"phone": "3001234567"})  # no change: no new row

    rows = list(
        db.scalars(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(records[0]["id"]),
                AuditLog.action == AuditAction.CONTACT_UPDATED.value,
            )
        )
    )
    assert len(rows) == 1
    assert rows[0].actor_id == user.id
    assert rows[0].changes == {"phone": {"old": None, "new": "3001234567"}}


# --- photo: uploads ------------------------------------------------------------


@pytest.mark.parametrize(
    ("content", "extension"), [(PNG, "png"), (JPEG, "jpg"), (WEBP, "webp")]
)
def test_supported_images_are_accepted(
    me: TestClient, storage: FakeStorage, content: bytes, extension: str
) -> None:
    response = _upload(me, content)

    assert response.status_code == 200
    assert response.json()["has_photo"] is True
    assert "photo_path" not in response.json()
    assert next(iter(storage.objects)).endswith(f".{extension}")


@pytest.mark.parametrize(
    "content",
    [
        b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
        b"<html><script>alert(1)</script></html>",
        b"MZ executable",
        b"",
        b"RIFF\x10\x00\x00\x00WAVE",
    ],
)
def test_real_content_decides_not_the_declared_type(
    me: TestClient, storage: FakeStorage, content: bytes
) -> None:
    # The client swears it is a PNG: the bytes say otherwise.
    assert _upload(me, content, "photo.png", "image/png").status_code == 415
    assert storage.objects == {}


def test_limit_is_two_megabytes(me: TestClient, storage: FakeStorage) -> None:
    padded = PNG + b"0" * (MAX_PHOTO_BYTES - len(PNG))
    assert _upload(me, padded).status_code == 200
    assert _upload(me, padded + b"0").status_code == 413


def test_the_client_name_never_reaches_the_path(
    me: TestClient, storage: FakeStorage, records: list[dict[str, Any]]
) -> None:
    _upload(me, PNG, "../../other/evil.php")

    path = next(iter(storage.objects))
    assert path.startswith(f"{records[0]['id']}/")
    assert "evil" not in path
    assert ".." not in path


def test_new_photo_replaces_the_old_file(me: TestClient, storage: FakeStorage) -> None:
    _upload(me, PNG)
    _upload(me, JPEG)
    assert list(storage.objects.values()) == [JPEG]


def test_failing_to_delete_the_old_file_keeps_the_new_photo(
    me: TestClient, storage: FakeStorage
) -> None:
    _upload(me, PNG)
    storage.fail_delete = True

    assert _upload(me, JPEG).status_code == 200
    assert me.get("/me/employee/photo").content == JPEG


def test_photo_change_is_audited(
    me: TestClient, storage: FakeStorage, db: Session, records: list[dict[str, Any]]
) -> None:
    _upload(me, PNG)
    row = db.scalars(
        select(AuditLog).where(
            AuditLog.entity_id == uuid.UUID(records[0]["id"]),
            AuditLog.action == AuditAction.PHOTO_UPDATED.value,
        )
    ).one()
    assert row.changes["photo"] == {"old": "False", "new": "True"}


# --- photo: reading ------------------------------------------------------------


def test_employee_reads_their_photo_with_a_safe_type(
    me: TestClient, storage: FakeStorage
) -> None:
    _upload(me, JPEG, "a.html", "text/html")

    response = me.get("/me/employee/photo")

    assert response.content == JPEG
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_no_photo_is_404(me: TestClient, storage: FakeStorage) -> None:
    assert me.get("/me/employee/photo").status_code == 404


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (UserRole.HR, 200),
        (UserRole.ADMIN, 200),
        (UserRole.MANAGER, 200),
        (UserRole.EMPLOYEE, 403),
    ],
)
def test_reading_someone_elses_photo_depends_on_the_role(
    client: TestClient,
    db: Session,
    password_hash: str,
    user: User,
    storage: FakeStorage,
    records: list[dict[str, Any]],
    role: UserRole,
    expected: int,
) -> None:
    _login(client, user)
    _upload(client, PNG)

    _login(client, make_user(db, password_hash, role))
    response = client.get(f"/employees/{records[0]['id']}/photo")

    assert response.status_code == expected


def test_an_employee_cannot_read_their_own_photo_by_id_either(
    me: TestClient, storage: FakeStorage, records: list[dict[str, Any]]
) -> None:
    _upload(me, PNG)
    assert me.get(f"/employees/{records[0]['id']}/photo").status_code == 403


# --- photo: Storage problems ---------------------------------------------------


def test_storage_failure_on_upload_is_a_generic_503_and_changes_nothing(
    me: TestClient,
    storage: FakeStorage,
    db: Session,
    records: list[dict[str, Any]],
) -> None:
    storage.fail_with = StorageError("internal detail")

    response = _upload(me, PNG)

    assert response.status_code == 503
    assert "internal detail" not in response.text
    employee = db.get(Employee, uuid.UUID(records[0]["id"]))
    assert employee is not None
    assert employee.photo_path is None


def test_storage_failure_on_read_is_503(me: TestClient, storage: FakeStorage) -> None:
    _upload(me, PNG)
    storage.fail_with = StorageError("internal detail")
    assert me.get("/me/employee/photo").status_code == 503


def test_without_configuration_photos_answer_503_and_the_rest_keeps_working(
    me: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def not_configured() -> None:
        raise StorageError("Storage is not configured")

    monkeypatch.setattr("app.api.me.get_photo_storage", not_configured)

    assert _upload(me, PNG).status_code == 503
    assert me.get("/me/employee").status_code == 200


def test_temporary_password_cannot_reach_contact_or_photo(
    client: TestClient, db: Session, user: User, storage: FakeStorage
) -> None:
    user.must_change_password = True
    db.commit()
    _login(client, user)

    assert client.patch("/me/employee", json={"phone": "3001234567"}).status_code == 403
    assert _upload(client, PNG).status_code == 403


# --- the real Storage client, against a fake HTTP server ------------------------


def test_real_client_calls_the_expected_url_with_the_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> httpx.Response:
        calls.append({"method": method, "url": url, **kwargs})
        return httpx.Response(200, content=b"ok", request=httpx.Request(method, url))

    monkeypatch.setattr(httpx, "request", fake_request)
    client = SupabasePhotoStorage("https://x.supabase.co/", SECRET_KEY, "photos")

    client.upload("a/b.png", PNG, "image/png")

    assert calls[0]["url"] == "https://x.supabase.co/storage/v1/object/photos/a/b.png"
    assert calls[0]["headers"]["Authorization"] == f"Bearer {SECRET_KEY}"
    assert calls[0]["headers"]["Content-Type"] == "image/png"
    assert client.download("a/b.png") == b"ok"


@pytest.mark.parametrize("failure", ["status", "network"])
def test_real_client_errors_never_carry_the_key_or_the_url(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    failure: str,
) -> None:
    def fake_request(method: str, url: str, **kwargs: Any) -> httpx.Response:
        if failure == "network":
            raise httpx.ConnectError(f"cannot reach {url} {SECRET_KEY}")
        return httpx.Response(500, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx, "request", fake_request)
    client = SupabasePhotoStorage("https://x.supabase.co", SECRET_KEY, "photos")

    with caplog.at_level(logging.DEBUG), pytest.raises(StorageError) as caught:
        client.download("a/b.png")

    assert SECRET_KEY not in str(caught.value)
    assert "supabase.co" not in str(caught.value)
    assert caught.value.__cause__ is None
    assert SECRET_KEY not in caplog.text


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (PNG, "png"),
        (JPEG, "jpg"),
        (WEBP, "webp"),
        (b"GIF89a", None),
        (b"", None),
    ],
)
def test_detect_image(content: bytes, expected: str | None) -> None:
    detected = detect_image(content)
    assert (detected[0] if detected else None) == expected
