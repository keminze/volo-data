from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from services.auth import decode_token, get_user_by_id
from services.auth import User as UserModel

# 公开接口（不需要认证）
PUBLIC_PATHS = {
    "/health",
    "/auth/register",
    "/auth/login",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
}

# 公开路径前缀
PUBLIC_PATH_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/",
)


def is_public_path(path: str) -> bool:
    """检查路径是否需要公开访问"""
    if path in PUBLIC_PATHS:
        return True
    for prefix in PUBLIC_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


# Bearer token 认证
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """获取当前认证用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证，请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效",
        )

    user = await get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[UserModel]:
    """获取当前用户（可选，未登录返回 None）"""
    if not credentials:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        return None

    user_id: str = payload.get("sub")
    if not user_id:
        return None

    user = await get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        return None

    return user