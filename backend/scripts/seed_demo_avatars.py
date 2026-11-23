"""Generate and upload deterministic geometric avatars for demo employees.

Usage (from backend/, with the virtual environment active):
    python -m scripts.seed_demo_avatars [--dry-run] [--limit N]

Selects up to N employees without a photo that show up across the demo screens
(seeded E2E accounts, recent hires/departures, approved vacations in the current
month, monthly anniversaries, and the first page of the directory), renders a
256x256 PNG per person with Pillow, uploads it through the same Storage client
and path format as PUT /me/employee/photo, and updates ``photo_path`` in one
transaction per employee.
"""

import argparse
import calendar
import colorsys
import io
import math
import random
import sys
import uuid
from collections.abc import Iterable
from datetime import date

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.api.employees import ANNIVERSARY_LIMIT, RECENT_LIMIT
from app.core.clock import today
from app.db.session import SessionLocal
from app.models.employee import Employee, EmployeeStatus
from app.models.user import User
from app.models.vacation import VacationRequest, VacationStatus
from app.services.photo_storage import PhotoStorage, StorageError, get_photo_storage
from scripts.e2e_seed import PEOPLE as E2E_PEOPLE

DEFAULT_LIMIT = 30
DIRECTORY_PAGE_SIZE = 10
AVATAR_SIZE = 256
INITIALS_FONT_SIZE = 96

# Soft, rich backgrounds that keep high contrast against white centered initials.
PALETTE: tuple[tuple[int, int, int], ...] = (
    (45, 91, 168),   # soft royal blue
    (30, 122, 100),  # sage emerald
    (176, 98, 44),   # warm terracotta
    (114, 78, 168),  # muted violet
    (172, 62, 86),   # dusty crimson
    (34, 118, 142),  # ocean teal
    (72, 84, 164),   # periwinkle indigo
    (142, 68, 138),  # soft plum
    (52, 112, 74),   # pine green
    (156, 108, 42),  # warm ochre
)

SHAPE_KINDS = ("circle", "ring", "triangle", "band")


def _hls_to_rgb255(hue: float, lightness: float, saturation: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return (round(r * 255), round(g * 255), round(b * 255))


def _accent_colors(base: tuple[int, int, int]) -> list[tuple[int, int, int]]:
    """Complementary and tonal accents derived from the base color."""
    hue, lightness, saturation = colorsys.rgb_to_hls(*(c / 255 for c in base))
    return [
        _hls_to_rgb255((hue + 0.5) % 1.0, min(0.72, lightness + 0.14), min(0.85, saturation * 0.95)),
        _hls_to_rgb255((hue + 0.12) % 1.0, min(0.78, lightness + 0.22), min(0.8, saturation * 0.85)),
        _hls_to_rgb255((hue - 0.14) % 1.0, max(0.24, lightness - 0.14), min(0.9, saturation * 1.05)),
    ]


def _initials(first_names: str, last_names: str) -> str:
    first = first_names.strip()[:1]
    last = last_names.strip()[:1]
    return f"{first}{last}".upper() or "?"


def render_avatar(employee_id: uuid.UUID, first_names: str, last_names: str) -> bytes:
    """Render a deterministic 256x256 geometric PNG with centered white initials."""
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError as exc:
        raise RuntimeError(
            "Pillow (>=10) is required to generate avatars. Install it with: pip install pillow"
        ) from exc

    # Seed from the integer UUID so output is identical across Python runs.
    rng = random.Random(employee_id.int)
    base_color = rng.choice(PALETTE)
    accents = _accent_colors(base_color)

    canvas = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (*base_color, 255))

    shape_count = rng.randint(2, 4)
    for _ in range(shape_count):
        overlay = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        color = rng.choice(accents)
        alpha = rng.randint(52, 96)
        rgba = (*color, alpha)
        kind = rng.choice(SHAPE_KINDS)

        if kind == "circle":
            cx = rng.randint(-24, AVATAR_SIZE + 24)
            cy = rng.randint(-24, AVATAR_SIZE + 24)
            radius = rng.randint(36, 108)
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=rgba)
        elif kind == "ring":
            cx = rng.randint(-16, AVATAR_SIZE + 16)
            cy = rng.randint(-16, AVATAR_SIZE + 16)
            radius = rng.randint(44, 114)
            stroke = rng.randint(6, 16)
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                outline=rgba,
                width=stroke,
            )
        elif kind == "triangle":
            cx = rng.randint(20, AVATAR_SIZE - 20)
            cy = rng.randint(20, AVATAR_SIZE - 20)
            radius = rng.randint(48, 108)
            base_angle = rng.uniform(0, math.tau)
            points = [
                (
                    cx + radius * math.cos(base_angle + i * (math.tau / 3)),
                    cy + radius * math.sin(base_angle + i * (math.tau / 3)),
                )
                for i in range(3)
            ]
            draw.polygon(points, fill=rgba)
        else:  # band
            theta = rng.uniform(0, math.pi)
            dx, dy = math.cos(theta), math.sin(theta)
            nx, ny = -dy, dx
            offset = rng.uniform(-90, 90)
            half_width = rng.uniform(14, 34)
            half_length = float(AVATAR_SIZE)
            mx = AVATAR_SIZE / 2 + offset * nx
            my = AVATAR_SIZE / 2 + offset * ny
            points = [
                (mx - half_length * dx - half_width * nx, my - half_length * dy - half_width * ny),
                (mx + half_length * dx - half_width * nx, my + half_length * dy - half_width * ny),
                (mx + half_length * dx + half_width * nx, my + half_length * dy + half_width * ny),
                (mx - half_length * dx + half_width * nx, my - half_length * dy + half_width * ny),
            ]
            draw.polygon(points, fill=rgba)

        canvas = Image.alpha_composite(canvas, overlay)

    initials = _initials(first_names, last_names)
    font = ImageFont.load_default(size=INITIALS_FONT_SIZE)
    measure = ImageDraw.Draw(canvas)
    bbox = measure.textbbox((0, 0), initials, font=font)
    text_x = (AVATAR_SIZE - (bbox[2] - bbox[0])) / 2 - bbox[0]
    text_y = (AVATAR_SIZE - (bbox[3] - bbox[1])) / 2 - bbox[1]

    shadow = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((text_x, text_y + 4), initials, font=font, fill=(0, 0, 0, 95))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=4))
    canvas = Image.alpha_composite(canvas, shadow)

    text_layer = Image.new("RGBA", (AVATAR_SIZE, AVATAR_SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(text_layer).text(
        (text_x, text_y), initials, font=font, fill=(255, 255, 255, 255)
    )
    canvas = Image.alpha_composite(canvas, text_layer)

    buffer = io.BytesIO()
    canvas.convert("RGB").save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _e2e_employees(db: Session) -> list[Employee]:
    """Employees linked to the seeded E2E accounts, preserving E2E_PEOPLE order."""
    emails = [person.email for person in E2E_PEOPLE]
    by_user = db.execute(
        select(User.email, Employee)
        .join(Employee, Employee.id == User.employee_id)
        .where(User.email.in_(emails))
    ).all()
    mapped: dict[str, Employee] = {email: employee for email, employee in by_user}

    by_email = db.scalars(select(Employee).where(Employee.email.in_(emails))).all()
    for employee in by_email:
        mapped.setdefault(employee.email, employee)

    return [mapped[email] for email in emails if email in mapped]


def _recent_hires(db: Session) -> list[Employee]:
    return list(
        db.scalars(
            select(Employee)
            .where(
                Employee.status == EmployeeStatus.ACTIVO,
                Employee.start_date <= func.current_date(),
            )
            .order_by(Employee.start_date.desc(), Employee.created_at.desc(), Employee.id)
            .limit(RECENT_LIMIT)
        )
    )


def _recent_departures(db: Session) -> list[Employee]:
    return list(
        db.scalars(
            select(Employee)
            .where(Employee.status == EmployeeStatus.INACTIVO)
            .order_by(Employee.end_date.desc().nulls_last(), Employee.last_names, Employee.id)
            .limit(RECENT_LIMIT)
        )
    )


def _approved_vacations_in_month(db: Session, reference: date) -> list[Employee]:
    first = date(reference.year, reference.month, 1)
    last = date(reference.year, reference.month, calendar.monthrange(reference.year, reference.month)[1])
    return list(
        db.scalars(
            select(Employee)
            .join(VacationRequest, VacationRequest.employee_id == Employee.id)
            .where(
                VacationRequest.status == VacationStatus.APROBADA,
                VacationRequest.start_date <= last,
                VacationRequest.end_date >= first,
            )
            .order_by(VacationRequest.start_date, Employee.last_names, Employee.first_names, Employee.id)
        )
    )


def _monthly_anniversaries(db: Session, reference: date) -> list[Employee]:
    return list(
        db.scalars(
            select(Employee)
            .where(
                Employee.status == EmployeeStatus.ACTIVO,
                extract("month", Employee.start_date) == reference.month,
                extract("year", Employee.start_date) < reference.year,
            )
            .order_by(
                extract("day", Employee.start_date),
                Employee.last_names,
                Employee.first_names,
                Employee.id,
            )
            .limit(ANNIVERSARY_LIMIT)
        )
    )


def _directory_first_page(db: Session) -> list[Employee]:
    return list(
        db.scalars(
            select(Employee)
            .order_by(Employee.last_names, Employee.first_names, Employee.id)
            .limit(DIRECTORY_PAGE_SIZE)
        )
    )


def select_candidates(db: Session, reference: date, limit: int) -> list[Employee]:
    """Up to `limit` unique employees without photos visible in demo flows."""
    if limit <= 0:
        return []
    groups: tuple[Iterable[Employee], ...] = (
        _e2e_employees(db),
        _recent_hires(db),
        _recent_departures(db),
        _approved_vacations_in_month(db, reference),
        _monthly_anniversaries(db, reference),
        _directory_first_page(db),
    )
    selected: list[Employee] = []
    seen: set[uuid.UUID] = set()
    for group in groups:
        for employee in group:
            if employee.id in seen or employee.photo_path is not None:
                continue
            seen.add(employee.id)
            selected.append(employee)
            if len(selected) >= limit:
                return selected
    return selected


def _photo_path_for(employee_id: uuid.UUID) -> str:
    # Same format as PUT /me/employee/photo.
    return f"{employee_id}/{uuid.uuid4().hex}.png"


def _upload_one(storage: PhotoStorage, employee_id: uuid.UUID, first_names: str, last_names: str) -> str:
    content = render_avatar(employee_id, first_names, last_names)
    path = _photo_path_for(employee_id)
    storage.upload(path, content, "image/png")

    with SessionLocal() as db:
        try:
            employee = db.get(Employee, employee_id)
            if employee is None or employee.photo_path is not None:
                try:
                    storage.delete(path)
                except StorageError:
                    pass
                return ""
            employee.photo_path = path
            db.commit()
        except Exception:
            db.rollback()
            try:
                storage.delete(path)
            except StorageError:
                pass
            raise
    return path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera y sube avatares PNG determinísticos para empleados de demostración sin foto."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista nombres y rutas planeadas sin subir archivos ni escribir en la base de datos.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Máximo de avatares a generar (por defecto {DEFAULT_LIMIT}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.limit < 0:
        print("--limit debe ser mayor o igual a 0.")
        return 1

    storage: PhotoStorage | None = None
    if not args.dry_run:
        try:
            storage = get_photo_storage()
        except StorageError as exc:
            print(f"Storage no está configurado: {exc}")
            print("Define SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY y SUPABASE_STORAGE_BUCKET.")
            return 1

    reference = today()
    with SessionLocal() as db:
        candidates = [
            (employee.id, employee.first_names, employee.last_names)
            for employee in select_candidates(db, reference, args.limit)
        ]

    if args.dry_run:
        for employee_id, first_names, last_names in candidates:
            path = _photo_path_for(employee_id)
            print(f"[dry-run] {first_names} {last_names} -> {path}")
        print(f"0 avatares subidos ({len(candidates)} pendientes en modo dry-run)")
        return 0

    assert storage is not None
    uploaded = 0
    for employee_id, first_names, last_names in candidates:
        try:
            saved_path = _upload_one(storage, employee_id, first_names, last_names)
        except RuntimeError as exc:
            print(str(exc))
            return 1
        except StorageError as exc:
            print(f"Error de Storage al subir {first_names} {last_names}: {exc}")
            if exc.detail:
                print(f"Detalle: {exc.detail}")
            print(f"{uploaded} avatares subidos")
            return 1
        if saved_path:
            uploaded += 1
            print(f"{first_names} {last_names} -> {saved_path}")

    print(f"{uploaded} avatares subidos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
