"""HU-2.6 and HU-2.7: what the signed-in person can see and edit about themselves.

These routes take no employee id. The record always comes from the session, so
there is no parameter a user could change to reach someone else's data (IDOR).
"""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.models.audit_log import AuditAction
from app.models.employee import Employee
from app.schemas.employee import ContactUpdate, EmployeeResponse
from app.services.audit import record_audit
from app.services.photo_storage import (
    MAX_PHOTO_BYTES,
    PhotoStorage,
    StorageError,
    content_type_of,
    detect_image,
    get_photo_storage,
)

router = APIRouter(prefix="/me", tags=["me"])

logger = logging.getLogger("tat.photos")


def photo_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Photo service is unavailable",
    )


def provide_storage() -> PhotoStorage:
    """A missing configuration is a 503 on these routes, not a crash of the API."""
    try:
        return get_photo_storage()
    except StorageError as exc:
        logger.error("%s", exc)
        raise photo_unavailable() from None


Storage = Annotated[PhotoStorage, Depends(provide_storage)]


def _own_employee(user: CurrentUser, db: DbSession) -> Employee:
    # An account may exist without a record, like the first administrator.
    employee = db.get(Employee, user.employee_id) if user.employee_id else None
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This account is not linked to an employee record",
        )
    return employee


def photo_response(employee: Employee, storage: PhotoStorage) -> Response:
    if employee.photo_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No photo")
    try:
        content = storage.download(employee.photo_path)
    except StorageError as exc:
        logger.error("%s", exc)
        raise photo_unavailable() from None
    return Response(content=content, media_type=content_type_of(employee.photo_path))


@router.get("/employee", response_model=EmployeeResponse)
def get_my_employee(current_user: CurrentUser, db: DbSession) -> Employee:
    return _own_employee(current_user, db)


@router.patch("/employee", response_model=EmployeeResponse)
def update_my_contact(
    data: ContactUpdate, request: Request, current_user: CurrentUser, db: DbSession
) -> Employee:
    """HU-2.7: contact fields only; saved at once in the shared employee record."""
    employee = _own_employee(current_user, db)

    changes: dict[str, tuple[object, object]] = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        if getattr(employee, field) != value:
            changes[field] = (getattr(employee, field), value)
            setattr(employee, field, value)

    if changes:
        record_audit(
            db,
            actor=current_user,
            request=request,
            action=AuditAction.CONTACT_UPDATED,
            entity_type="employee",
            entity_id=employee.id,
            changes=changes,
        )
        db.commit()
    return employee


@router.get("/employee/photo")
def get_my_photo(current_user: CurrentUser, db: DbSession, storage: Storage) -> Response:
    return photo_response(_own_employee(current_user, db), storage)


@router.put("/employee/photo", response_model=EmployeeResponse)
def update_my_photo(
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    storage: Storage,
    photo: Annotated[UploadFile, File()],
) -> Employee:
    employee = _own_employee(current_user, db)

    # One byte past the limit is enough to know it is too big, without reading it all.
    content = photo.file.read(MAX_PHOTO_BYTES + 1)
    if len(content) > MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The photo must not exceed 2 MB",
        )
    image = detect_image(content)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The photo must be a JPEG, PNG or WEBP image",
        )
    extension, content_type = image

    # A new random name per upload: the client controls no part of the path.
    new_path = f"{employee.id}/{uuid.uuid4().hex}.{extension}"
    try:
        storage.upload(new_path, content, content_type)
    except StorageError as exc:
        logger.error("%s", exc)
        raise photo_unavailable() from None

    old_path = employee.photo_path
    employee.photo_path = new_path
    record_audit(
        db,
        actor=current_user,
        request=request,
        action=AuditAction.PHOTO_UPDATED,
        entity_type="employee",
        entity_id=employee.id,
        changes={"photo": (old_path is not None, True)},
    )
    db.commit()

    # After the commit: if this fails, the record still points at a valid photo
    # and the only cost is one leftover file.
    if old_path is not None:
        try:
            storage.delete(old_path)
        except StorageError as exc:
            logger.warning("old photo not removed: %s", exc)
    return employee
