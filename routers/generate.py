import asyncio
import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select

from config.database import AsyncSession, async_session, get_db
from config.logging_config import logger
from config.models import Conversation, DBConnection, Message
from config.parameter import GenerateRequest
from redis_client import redis_client
from services.graph_sse import graph as graph_sse

router = APIRouter()


async def background_graph_task(task_id: str, conversation_id: int, state: dict, input_text: str):
    """
    独立于 HTTP 请求运行的后台任务
    """
    final_state = None
    try:
        # 1. 运行 AI 图计算并推送到 Redis
        async for mode, chunk in graph_sse.astream(state, stream_mode=["custom", "values"]):
            # 在 graph_sse 中已经将 chunk 推送到了 Redis，因此这里不需要再次推送
            if mode == "values":
                final_state = chunk

        # 2. 任务完成后，使用独立的 Session 保存数据库
        async with async_session() as db:
            # 保存用户消息
            new_user_message = Message(
                conversation_id=conversation_id, role="user", content=input_text
            )
            db.add(new_user_message)

            if final_state:
                # 保存 AI 消息
                new_ai_message = Message(
                    conversation_id=conversation_id,
                    role="ai",
                    sql=final_state.get("sql"),
                    content=final_state.get("report", ""),
                    sample_data=final_state.get("data", {}).get("data"),
                    charts=final_state.get("charts"),
                    compute_code=final_state.get("compute_code"),
                    code_result=final_state.get("code_result"),
                )
                db.add(new_ai_message)

            await db.commit()

        # 3. 标记 Redis 任务结束
        await redis_client.rpush(f"task_stream:{task_id}", "DONE")  # type: ignore
        logger.info(f"Task {task_id} completed successfully.")

    except Exception as e:
        # 记录异常并推送到 Redis
        logger.error(f"Background task {task_id} failed: {str(e)}", exc_info=True)
        error_message = json.dumps({"error": str(e)})
        await redis_client.rpush(f"task_stream:{task_id}", error_message)  # type: ignore
        logger.error(f"Error message pushed to Redis for task {task_id}: {error_message}")


@router.post("/stream", summary="流式调用生成接口")
async def run_query_stream(
    req: GenerateRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
):
    try:
        # 从数据库加载对话历史
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == req.conversation_id)
            .where(Conversation.user_id == req.user_id)
        )
        conversation = result.scalars().first()
        if not conversation:
            logger.error(f"Conversation {req.conversation_id} not found")
            return JSONResponse(status_code=404, content={"error": "Conversation not found"})
        if conversation.connection_id is None:
            logger.error(f"Conversation {req.conversation_id} has no associated connection")
            return JSONResponse(
                status_code=404, content={"error": "Conversation has no associated connection"}
            )

        result = await db.execute(
            select(DBConnection).where(DBConnection.id == conversation.connection_id)
        )
        connection = result.scalars().first()
        if not connection:
            logger.error(f"Connection {conversation.connection_id} not found")
            return JSONResponse(status_code=404, content={"error": "Connection not found"})

        collection_prefix = connection.collection_prefix
        if not collection_prefix:
            logger.error(f"Connection {connection.id} has no collection prefix")
            return JSONResponse(
                status_code=404, content={"error": "Connection has no collection prefix"}
            )

        result = await db.execute(
            select(Message.content)
            .where(Message.conversation_id == req.conversation_id)
            .where(Message.role == "user")
            .order_by(Message.created_at.desc())
            .limit(10)
        )
        user_history_list = result.scalars().all()

        task_id = str(uuid.uuid4())
        state = {
            "task_id": task_id,
            "input": req.input,
            "collection_prefix": collection_prefix,
            "db_params": connection.get_db_info(),
            "allow_llm_to_see_data": req.allow_llm_to_see_data,
            "user_history": user_history_list,
            "skip_charts": req.skip_charts,
            "skip_report": req.skip_report,
        }

        # 2. 启动后台任务
        background_tasks.add_task(
            background_graph_task, task_id, req.conversation_id, state, req.input
        )

        # 3. 立即返回 task_id
        return JSONResponse(content={"task_id": task_id})

    except Exception as e:
        logger.error(f"Error running query: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/task_stream/{task_id}")
async def get_task_stream(task_id: str, request: Request):
    async def event_generator():
        # 超时时间（秒）
        idle_start = asyncio.get_event_loop().time()
        MAX_IDLE = 60  # 超过 60s 无新事件退出

        while True:
            # ✓ 客户端断开连接时退出
            if await request.is_disconnected():
                break

            # 带 timeout 的 blpop
            result = await redis_client.blpop(f"task_stream:{task_id}", timeout=5)

            if result:
                _, data = result

                # DONE 标记结束流
                if data == "DONE":
                    break

                json_data = json.loads(data)
                yield (
                    f"event: {json_data['event']}\n" f"data: {json.dumps(json_data['data'])}\n\n"
                )

                # 有新消息则重置 idle 时间
                idle_start = asyncio.get_event_loop().time()
            else:
                # 超时未收到新消息
                if asyncio.get_event_loop().time() - idle_start > MAX_IDLE:
                    # 可发送 timeout 通知
                    yield "event: timeout\ndata: {}\n\n"
                    break

                # 睡眠小段时间继续循环
                await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
