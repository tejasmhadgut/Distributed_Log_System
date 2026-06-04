from fastapi import APIRouter, HTTPException, Depends
from src.api.dependencies import require_permission
from src.models.auth import UserResponse, UpdateRoleRequest
from src.models.permission import Role
from src.db.postgres import get_all_users, get_user_by_id, update_user_role, deactivate_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", dependencies=[Depends(require_permission("users:manage"))])
async def list_users():
    try:
        rows = get_all_users()
        return {
            "users": [
                {
                    "user_id": r[0], "username": r[1], "email": r[2],
                    "role": r[3], "is_active": r[4],
                    "created_at": r[5].isoformat() if r[5] else None
                }
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/role", response_model=UserResponse, dependencies=[Depends(require_permission("users:manage"))])
async def change_role(user_id: int, body: UpdateRoleRequest):
    try:
        if body.role not in [r.value for r in Role]:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {[r.value for r in Role]}")

        user = update_user_role(user_id, body.role)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/deactivate", dependencies=[Depends(require_permission("users:manage"))])
async def deactivate(user_id: int):
    try:
        if not deactivate_user(user_id):
            raise HTTPException(status_code=404, detail="User not found")
        return {"deactivated": True, "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
