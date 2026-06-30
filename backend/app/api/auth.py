"""Authentication, JWT issuance/verification, and RBAC."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import MAX_JWT_LIFETIME_HOURS, Settings
from ..db.models import User
from ..db.session import get_session

logger = logging.getLogger("backend.auth")

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


class AuthError(Exception):
    pass


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)


def create_access_token(settings: Settings, *, subject: str, role: str) -> str:
    lifetime = settings.jwt_lifetime_hours
    if lifetime > MAX_JWT_LIFETIME_HOURS:
        # Reject, never clamp.
        raise AuthError(
            f"Configured JWT lifetime {lifetime}h exceeds maximum {MAX_JWT_LIFETIME_HOURS}h"
        )
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=lifetime)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(settings: Settings, token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid token") from exc


# ---- FastAPI dependencies (wired with settings in main via app.state) -------

def get_settings_dep(request: Request) -> Settings:  # pragma: no cover - trivial
    return request.app.state.settings


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_session),
) -> User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    settings: Settings = request.app.state.settings
    try:
        payload = decode_token(settings, token)
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc))
    user = db.execute(select(User).where(User.email == payload["sub"])).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_role(*roles: str):
    """Dependency factory enforcing that the user has one of `roles`."""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if roles and user.role not in roles and user.role != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return _dep
