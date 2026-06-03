from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.core.auth import decode_token
from src.core.exceptions import AuthenticationError, AuthorizationError
from src.models.permission import ROLE_PERMISSIONS


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
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        allowed = ROLE_PERMISSIONS.get(user["role"], [])
        if permission not in allowed:
            raise AuthorizationError(f"Required permission: {permission}")
        return user
    return dependency