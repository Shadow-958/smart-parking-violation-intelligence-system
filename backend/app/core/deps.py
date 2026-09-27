"""
Reusable FastAPI dependencies for auth.

`get_current_user` is the base dependency every protected route uses.
`require_roles(...)` builds a stricter dependency for endpoints that only
officers/admins (e.g.) should reach — e.g.
`Depends(require_roles(UserRole.OFFICER, UserRole.ADMIN))`.
"""

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User, UserRole

# tokenUrl is used only to populate the "Authorize" button in Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
# auto_error=False so requests with no token don't raise 401 — used where
# a route works for both logged-in and anonymous callers (e.g. complaint
# submission via a channel with no account, like email or social media).
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except ValueError:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user = db.get(User, uuid.UUID(user_id))
    except ValueError:
        raise credentials_exception

    if user is None or not user.is_active:
        raise credentials_exception

    return user


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user, but returns None instead of raising 401 when
    no token is supplied. Used by routes that accept both authenticated
    and anonymous callers."""
    if not token:
        return None
    try:
        return get_current_user(token=token, db=db)
    except HTTPException:
        return None


def require_roles(*allowed_roles: UserRole):
    """Dependency factory: restricts an endpoint to the given roles."""

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _check
