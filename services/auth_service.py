"""Authentication service — register, login, token verification."""

import os
import re
import jwt
from datetime import datetime, timezone, timedelta
from .exceptions import AuthError, ValidationError
from models import db, User

SECRET_KEY = os.getenv("SECRET_KEY", "spendwise-dev-secret-change-in-production")
TOKEN_EXPIRY_HOURS = 72


def _generate_token(user_id: int) -> str:
    """Create a signed JWT for the given user."""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_token(token: str) -> int:
    """Decode a JWT and return the user_id. Raises AuthError if invalid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired — please log in again")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token — please log in again")


def register(data: dict) -> dict:
    """Create a new user account. Returns { user, token }."""
    errors = {}

    name = (data.get("name") or "").strip()
    if not name:
        errors["name"] = "name is required"
    elif len(name) > 100:
        errors["name"] = "name must be ≤ 100 characters"

    email = (data.get("email") or "").strip().lower()
    if not email:
        errors["email"] = "email is required"
    elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors["email"] = "invalid email format"
    elif len(email) > 255:
        errors["email"] = "email must be ≤ 255 characters"

    password = data.get("password") or ""
    if not password:
        errors["password"] = "password is required"
    elif len(password) < 6:
        errors["password"] = "password must be at least 6 characters"
    elif len(password) > 128:
        errors["password"] = "password must be ≤ 128 characters"

    if errors:
        raise ValidationError(errors)

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        raise ValidationError({"email": "an account with this email already exists"})

    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = _generate_token(user.id)
    return {"user": user.to_dict(), "token": token}


def login(data: dict) -> dict:
    """Authenticate a user. Returns { user, token }."""
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        raise AuthError("Email and password are required")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        raise AuthError("Invalid email or password")

    token = _generate_token(user.id)
    return {"user": user.to_dict(), "token": token}


def get_user_by_id(user_id: int) -> dict:
    """Get a user's profile by ID."""
    user = db.session.get(User, user_id)
    if not user:
        raise AuthError("User not found")
    return user.to_dict()
