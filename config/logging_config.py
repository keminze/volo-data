import contextvars
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

# 存储 request_id 的上下文变量
request_id_ctx = contextvars.ContextVar("request_id", default="-")

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(request_id)s] %(message)s"


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get("-")
        return True


def setup_logger():
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(LOG_FORMAT)

    # 控制台日志
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIdFilter())

    # 文件日志（每天新建一个文件，保存最近 7 天）
    file_handler = TimedRotatingFileHandler(
        filename="logs/app.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(RequestIdFilter())

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
