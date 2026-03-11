import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED

# 不需要鉴权的接口
EXCLUDE_PATHS = {"/health"}


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # ✅ 跳过 OPTIONS 预检请求（CORS 会自动处理）
        if request.method == "OPTIONS":
            return await call_next(request)

        # ✅ 跳过无需鉴权的接口
        if request.url.path in EXCLUDE_PATHS:
            return await call_next(request)

        # ✅ 从请求头中获取 API Key
        api_key = request.headers.get("x-api-key")

        # ✅ 从环境变量获取合法的 API Key
        expected_key = os.getenv("API_KEY")

        # ✅ 打印调试信息（仅显示前几位）
        print(f"[APIKeyAuth] Received key: {api_key[:6] + '***' if api_key else None}")

        # ✅ 校验 API Key
        if not api_key or api_key != expected_key:
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={"detail": "无效或缺失的 API Key"},
            )

        # ✅ 通过验证，继续执行下一个中间件/路由
        return await call_next(request)
