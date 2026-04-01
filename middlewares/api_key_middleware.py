import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED

# 公开接口（不需要鉴权）
PUBLIC_PATHS = {
    "/health",
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


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 跳过 OPTIONS 预检请求
        if request.method == "OPTIONS":
            return await call_next(request)

        # 跳过无需鉴权的接口
        if is_public_path(request.url.path):
            return await call_next(request)

        # 优先使用 JWT Bearer Token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # JWT 认证由 dependencies.py 中的 get_current_user 处理
            # 这里只做初步检查，如果有 Bearer token 就放行
            return await call_next(request)

        # 备选：API Key 认证
        api_key = request.headers.get("x-api-key")
        expected_key = os.getenv("API_KEY")

        if api_key and api_key == expected_key:
            return await call_next(request)

        # 两个认证都没有通过
        return JSONResponse(
            status_code=HTTP_401_UNAUTHORIZED,
            content={"detail": "未认证，请登录或提供有效的 API Key"},
        )
