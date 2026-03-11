import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config.logging_config import logger, request_id_ctx


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request_id_ctx.set(request_id)  # 设置到上下文
        request.state.request_id = request_id

        start = time.time()
        logger.info(f"➡️ {request.method} {request.url.path}")

        response: Response = await call_next(request)

        duration = round(time.time() - start, 3)
        logger.info(
            f"⬅️ {request.method} {request.url.path} "
            f"status={response.status_code} duration={duration}s"
        )

        response.headers["X-Request-ID"] = request_id
        return response
