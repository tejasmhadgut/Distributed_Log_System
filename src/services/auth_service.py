from datetime import datetime, timedelta, timezone
from src.config.settings import get_settings
from src.core.auth import verify_password, create_access_token, create_refresh_token, decode_token
from src.core.exceptions import AuthenticationError
from src.db.postgres import (
    get_user_by_username, get_user_by_id,
    store_refresh_token, verify_refresh_token, revoke_refresh_token
)
from src.models.auth import TokenResponse


def login(username: str, password: str) -> TokenResponse:
    user = get_user_by_username(username)
    if not user or not verify_password(password, user["hashed_password"]):
        raise AuthenticationError("Invalid username or password")

    if not user["is_active"]:
        raise AuthenticationError("Account is disabled")

    access_token = create_access_token(user["user_id"], user["username"], user["role"])
    refresh_token = create_refresh_token(user["user_id"])

    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    store_refresh_token(user["user_id"], refresh_token, expires_at)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def refresh(refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise AuthenticationError("Invalid token type")

    if not verify_refresh_token(refresh_token):
        raise AuthenticationError("Token has been revoked")

    user = get_user_by_id(int(payload["sub"]))
    if not user:
        raise AuthenticationError("User not found")

    # Rotate — revoke old, issue new
    revoke_refresh_token(refresh_token)
    new_access = create_access_token(user["user_id"], user["username"], user["role"])
    new_refresh = create_refresh_token(user["user_id"])

    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    store_refresh_token(user["user_id"], new_refresh, expires_at)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


def logout(refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") == "refresh":
            revoke_refresh_token(refresh_token)
    except AuthenticationError:
        pass  # already invalid, logout still succeeds
