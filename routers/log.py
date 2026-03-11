import asyncio
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter()

LOG_DIR = Path("logs")
LOG_FILE_NAME = "app.log"


# 🔹1. 异步获取日志文件列表
@router.get("/files", summary="获取日志文件列表")
async def list_log_files():
    if not LOG_DIR.exists():
        return {"files": []}

    # 异步丢线程池读取目录
    files = await asyncio.to_thread(
        lambda: sorted([f.name for f in LOG_DIR.glob("*.log*")], reverse=True)
    )
    return {"files": files}


@router.get("/view", summary="查看日志（不筛选）")
async def view_logs(
    file_name: str = Query(LOG_FILE_NAME, description="日志文件名"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    log_path = LOG_DIR / file_name
    if not log_path.exists():
        return JSONResponse(status_code=404, content={"error": f"Log file {file_name} not found"})

    # 使用生成器方式，避免一次性加载整个文件（内存友好）
    def read_logs(limit: int, offset: int):
        logs = []
        with open(log_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < offset:
                    continue
                if i >= offset + limit:
                    break
                logs.append(line.rstrip("\n"))
        return logs

    # 计算总行数（也放到线程中防止阻塞）
    def count_lines():
        with open(log_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)

    total, data = await asyncio.gather(
        asyncio.to_thread(count_lines), asyncio.to_thread(read_logs, limit, offset)
    )

    return {"file": file_name, "total": total, "offset": offset, "limit": limit, "logs": data}
