import argparse

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.database import del_single_table, init_db
from middlewares.api_key_middleware import APIKeyAuthMiddleware
from middlewares.logging import LoggingMiddleware
from routers import connection, conversation, database, generate, log

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 临时全放开
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # 必须包括 x-api-key
)
app.add_middleware(APIKeyAuthMiddleware)
app.add_middleware(LoggingMiddleware)


@app.on_event("startup")
async def on_startup():
    # await del_db()
    # print("重置数据库")
    await del_single_table("messages")
    await init_db()
    print("数据库初始化完成")


app.include_router(connection.router, prefix="/connections", tags=["数据源连接管理"])
app.include_router(conversation.router, prefix="/conversations", tags=["对话管理"])
app.include_router(generate.router, prefix="/generate", tags=["任务生成"])
app.include_router(database.router, prefix="/database", tags=["系统数据库管理"])
app.include_router(log.router, prefix="/log", tags=["日志管理"])


@app.get("/health", tags=["服务检测"])
async def root():
    return {"msg": "VoloDate Service is running"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9000, help="Server port")
    args = parser.parse_args()

    uvicorn.run("main:app", host="0.0.0.0", port=args.port)
