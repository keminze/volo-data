import asyncio
import re
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter()

LOG_DIR = Path("logs")
LOG_FILE_NAME = "app.log"


# 🔹1. 异步获取日志文件列表
@router.get("/files")
async def list_log_files():
    if not LOG_DIR.exists():
        return {"files": []}

    # 异步丢线程池读取目录
    files = await asyncio.to_thread(
        lambda: sorted([f.name for f in LOG_DIR.glob("*.log*")], reverse=True)
    )
    return {"files": files}


# 🔹2. 异步过滤查看日志
@router.get("/view")
async def view_logs(
    file_name: str = Query(LOG_FILE_NAME, description="日志文件名"),
    level: str = Query(None, description="日志级别，如 INFO/ERROR/WARNING"),
    request_id: str = Query(None, description="按 request_id 过滤"),
    keyword: str = Query(None, description="关键字搜索"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    log_path = LOG_DIR / file_name
    if not log_path.exists():
        return JSONResponse(status_code=404, content={"error": f"Log file {file_name} not found"})

    # 定义阻塞的读取 + 过滤函数
    def read_logs():
        matched = []
        log_regex = re.compile(
            r"\[(?P<time>.*?)\]\s+\[(?P<level>\w+)\]\s+\[(?P<reqid>[^\]]*)\]\s+(?P<msg>.*)"
        )
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                m = log_regex.match(line)
                if not m:
                    continue
                row = m.groupdict()
                if level and row["level"].upper() != level.upper():
                    continue
                if request_id and row["reqid"] != request_id:
                    continue
                if keyword and keyword not in row["msg"]:
                    continue
                matched.append(row)
        return matched

    # 异步执行阻塞操作
    matched = await asyncio.to_thread(read_logs)

    total = len(matched)
    data = matched[offset : offset + limit]

    return {"file": file_name, "total": total, "offset": offset, "limit": limit, "logs": data}
