from fastapi import APIRouter, Depends
from app.api import deps
from app.models.user import User

router = APIRouter()

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(deps.get_current_user)):
    """
    Get current user.
    """
    return current_user

@router.get("/admin-dashboard", dependencies=[Depends(deps.get_current_admin)])
async def admin_dashboard_stats():
    """
    Example protected admin route.
    """
    return {"msg": "Welcome Admin", "stats": "Everything is good"}
