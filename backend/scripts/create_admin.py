"""Create the first ADMIN user (there is no public sign-up in TAT).

Usage (from backend/):
    python -m scripts.create_admin
"""

from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole

MIN_PASSWORD_LENGTH = 12


def main() -> None:
    email = input("Admin email: ").strip().lower()
    full_name = input("Full name: ").strip()
    # getpass hides the input and keeps the password out of shell history.
    password = getpass("Password: ")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if password != getpass("Repeat password: "):
        raise SystemExit("Passwords do not match")

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)) is not None:
            raise SystemExit(f"User {email} already exists")

        db.add(
            User(
                email=email,
                full_name=full_name,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
            )
        )
        db.commit()

    print(f"Admin {email} created")


if __name__ == "__main__":
    main()
