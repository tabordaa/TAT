"""Public holidays (HU-4.6): days that are not counted as vacation days."""

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Holiday(Base):
    __tablename__ = "holidays"

    # The date itself is the key: a day is a holiday or it is not.
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
