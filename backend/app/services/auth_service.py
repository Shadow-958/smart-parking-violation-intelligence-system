"""
Authentication business logic. Kept separate from app/api/routes/auth.py
so it's reusable (e.g. by an admin "create officer account" endpoint later)
and independently testable without spinning up FastAPI.
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


class DuplicateUserError(Exception):
    """Raised when a username or email is already registered."""


class InvalidCredentialsError(Exception):
    """Raised for a wrong username/password or an inactive account."""


def create_user(db: Session, user_in: UserCreate) -> User:
    existing = (
        db.query(User)
        .filter(or_(User.username == user_in.username, User.email == user_in.email))
        .first()
    )
    if existing is not None:
        raise DuplicateUserError("Username or email is already registered")

    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.hashed_password):
        # Deliberately the same error/message for "no such user" and "wrong
        # password" so a login attempt can't be used to enumerate usernames.
        raise InvalidCredentialsError("Incorrect username or password")
    if not user.is_active:
        raise InvalidCredentialsError("This account has been deactivated")
    return user
