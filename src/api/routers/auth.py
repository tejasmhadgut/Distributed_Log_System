from fastapi import APIRouter, Depends
from src.models.auth import LoginRequest, RefreshRequest, TokenResponse, RegisterRequest, UserResponse
from src.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    return auth_service.login(request.username, request.password)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest):
    return auth_service.refresh(request.refresh_token)

@router.post("/logout")
async def logout(request: RefreshRequest):
    auth_service.logout(request.refresh_token)
    return {"logged_out": True}

@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest):
    return auth_service.register(request.username, request.email, request.password)
