"""API contracts for public holidays (HU-4.6)."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class HolidayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    name: str


class HolidayCreate(BaseModel):
    """An ADMIN adds a holiday, e.g. one declared by decree."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    day: date
    name: str = Field(min_length=3, max_length=80)
