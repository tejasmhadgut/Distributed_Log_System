from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.core.auth import decode_token
from src.core.exceptions import AuthenticationError, AuthorizationError
from src.core.rate_limiter import check_rate_limit
from src.models.permission import ROLE_PERMISSIONS
from src.services.cache_service import get_redis
from src.config.settings import get_settings

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    return {
        "user_id": int(payload["sub"]),
        "username": payload["username"],
        "role": payload["role"]
    }

def require_permission(permission: str):
    def dependency(user: dict = Depends(rate_limit)) -> dict:
        allowed = ROLE_PERMISSIONS.get(user["role"], [])
        if permission not in allowed:
            raise AuthorizationError(f"Required permission: {permission}")
        return user
    return dependency


def rate_limit(user: dict = Depends(get_current_user)) -> dict:
    settings = get_settings()
    if settings.RATE_LIMIT_ENABLED:
        try:
            r = get_redis()
            check_rate_limit(user["user_id"], r, settings.RATE_LIMIT_REQUESTS_PER_MINUTE)
        except Exception as e:
            from src.core.exceptions import RateLimitError
            if isinstance(e, RateLimitError):
                raise
            # Redis down — fail open, let request through
    return user