"""HU-4.6: Colombian public holidays, which are not vacation days.

Colombia has 18 holidays a year, of three kinds (Ley 51 de 1983, "Ley Emiliani"):

- 6 on a fixed date, whatever the weekday.
- 7 that move to the next Monday when they do not fall on one.
- 5 that depend on Easter Sunday: Holy Thursday and Good Friday stay where they
  are; Ascension, Corpus Christi and Sacred Heart are moved to a Monday.

The function only calculates. What the system uses is the `holidays` table,
seeded with these dates by a migration and editable by an ADMIN, because the
government can add a holiday by decree and a formula would never know.
"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.holiday import Holiday

FIXED = (
    (1, 1, "Año Nuevo"),
    (5, 1, "Día del Trabajo"),
    (7, 20, "Día de la Independencia"),
    (8, 7, "Batalla de Boyacá"),
    (12, 8, "Inmaculada Concepción"),
    (12, 25, "Navidad"),
)

MOVED_TO_MONDAY = (
    (1, 6, "Día de los Reyes Magos"),
    (3, 19, "Día de San José"),
    (6, 29, "San Pedro y San Pablo"),
    (8, 15, "La Asunción de la Virgen"),
    (10, 12, "Día de la Raza"),
    (11, 1, "Todos los Santos"),
    (11, 11, "Independencia de Cartagena"),
)

# Days after Easter Sunday, and whether the holiday moves to a Monday.
FROM_EASTER = (
    (-3, False, "Jueves Santo"),
    (-2, False, "Viernes Santo"),
    (39, True, "Ascensión del Señor"),
    (60, True, "Corpus Christi"),
    (68, True, "Sagrado Corazón de Jesús"),
)


def easter_sunday(year: int) -> date:
    """Gregorian Easter (the anonymous algorithm published by Meeus and Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    leap = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * leap) // 451
    month, day = divmod(h + leap - 7 * m + 114, 31)
    return date(year, month, day + 1)


def next_monday(day: date) -> date:
    """The same day if it is a Monday; otherwise the Monday after it."""
    return day + timedelta(days=(7 - day.weekday()) % 7)


def colombian_holidays(year: int) -> list[tuple[date, str]]:
    """The holidays of `year`, one entry per day, ordered by date.

    Usually 18 days. When two holidays land on the same Monday (in 2025 Sacred
    Heart and Saint Peter both fell on June 30) they are one day off, not two:
    the names are joined and that year has 17 days.
    """
    names: dict[date, list[str]] = {}

    def add(day: date, name: str) -> None:
        names.setdefault(day, []).append(name)

    for month, day_of_month, name in FIXED:
        add(date(year, month, day_of_month), name)
    for month, day_of_month, name in MOVED_TO_MONDAY:
        add(next_monday(date(year, month, day_of_month)), name)
    easter = easter_sunday(year)
    for offset, moves, name in FROM_EASTER:
        moved = easter + timedelta(days=offset)
        add(next_monday(moved) if moves else moved, name)
    return [(day, " y ".join(names[day])) for day in sorted(names)]


def holidays_between(db: Session, start: date, end: date) -> set[date]:
    """The holidays stored in the table between both dates, in one query."""
    return set(db.scalars(select(Holiday.day).where(Holiday.day >= start, Holiday.day <= end)))
