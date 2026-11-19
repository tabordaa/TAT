"""HU-4.6: public holidays. Everyone reads them (the vacation form counts days
with them); only an ADMIN changes them."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy import extract, select

from app.api.deps import Admin, CurrentUser, DbSession
from app.models.audit_log import AuditAction
from app.models.holiday import Holiday
from app.schemas.holiday import HolidayCreate, HolidayResponse
from app.services.audit import record_audit

router = APIRouter(prefix="/holidays", tags=["holidays"])

# The audit log points to rows by UUID; a holiday's key is its date. A name-based
# UUID gives the same id for the same day, so its whole history can be followed.
_HOLIDAY_NAMESPACE = uuid.UUID("6f1d3c52-8a4e-4b7f-9c21-0d5e8f3a7b64")


def holiday_entity_id(day: date) -> uuid.UUID:
    return uuid.uuid5(_HOLIDAY_NAMESPACE, day.isoformat())


@router.get("", response_model=list[HolidayResponse])
def list_holidays(
    db: DbSession,
    current_user: CurrentUser,  # any session: the vacation form needs them
    year: Annotated[int, Query(ge=2000, le=2100)],
) -> list[Holiday]:
    return list(
        db.scalars(select(Holiday).where(extract("year", Holiday.day) == year).order_by(Holiday.day))
    )


@router.post("", response_model=HolidayResponse, status_code=status.HTTP_201_CREATED)
def add_holiday(
    data: HolidayCreate, request: Request, db: DbSession, current_user: Admin
) -> Holiday:
    """CA01: e.g. a holiday declared by decree, or the seed of a new year."""
    if db.get(Holiday, data.day) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"field": "day", "message": "That day is already a holiday"},
        )
    holiday = Holiday(day=data.day, name=data.name)
    db.add(holiday)
    record_audit(
        db,
        actor=current_user,
        request=request,
        action=AuditAction.HOLIDAY_ADDED,
        entity_type="holiday",
        entity_id=holiday_entity_id(data.day),
        changes={"day": (None, data.day), "name": (None, data.name)},
    )
    db.commit()
    return holiday


@router.delete("/{day}", status_code=status.HTTP_204_NO_CONTENT)
def remove_holiday(day: date, request: Request, db: DbSession, current_user: Admin) -> Response:
    """Requests already made keep their business days: they were counted with
    the holidays of that moment, and changing them now would move balances."""
    holiday = db.get(Holiday, day)
    if holiday is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday not found")
    record_audit(
        db,
        actor=current_user,
        request=request,
        action=AuditAction.HOLIDAY_REMOVED,
        entity_type="holiday",
        entity_id=holiday_entity_id(day),
        changes={"day": (day, None), "name": (holiday.name, None)},
    )
    db.delete(holiday)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
