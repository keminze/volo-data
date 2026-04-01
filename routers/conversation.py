from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from config.logging_config import logger
from config.models import Conversation, DBConnection, Message
from config.parameter import ConversationCreate
from dependencies import get_current_user
from services.auth import User
from services.tools import generate_chart_tool

# from sqlalchemy.orm import joinedload
# from fastapi.concurrency import run_in_threadpool

router = APIRouter()


@router.post("/create", summary="创建新的对话")
async def create_conversation(
    req: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        conn = await db.execute(select(DBConnection).where(DBConnection.id == req.connection_id))
        connection = conn.scalar_one_or_none()
        if not connection:
            return JSONResponse(status_code=404, content="Not found connection")
        if connection.user_id != str(current_user.id):
            return JSONResponse(status_code=404, content="Not found connection")

        new_conversation = Conversation(
            user_id=str(current_user.id),
            # collection_prefix=collection_prefix,
            name=req.name,
            connection_id=req.connection_id,
            description=req.description,
        )
        db.add(new_conversation)
        await db.commit()
        await db.refresh(new_conversation)
        logger.info(
            f"Created new conversation with ID: {new_conversation.id} for user_id: {current_user.id}"
        )
        return JSONResponse(
            content={"message": "conversation created", "conversation_id": new_conversation.id}
        )
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content="Error creating conversation")


@router.get("/list", summary="列出用户所有对话")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == str(current_user.id))
            .order_by(Conversation.created_at.desc())
        )
        conversations = result.scalars().all()
        logger.info(f"Listed {len(conversations)} conversations for user_id: {current_user.id}")
        return [c.get_info() for c in conversations]
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content="Error listing conversations")


@router.delete("/delete/{conversation_id}", summary="删除对话")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.user_id == str(current_user.id))
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            logger.warning(f"Conversation ID {conversation_id} not found for deletion")
            return JSONResponse(status_code=404, content={"error": "Conversation not found"})
        await db.delete(conversation)
        await db.commit()
        logger.info(f"Deleted conversation with ID: {conversation_id}")
        return JSONResponse("conversation deleted")
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Error deleting conversation"})


@router.get("/{conversation_id}", summary="获取对话详情")
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.user_id == str(current_user.id))
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            logger.warning(f"Conversation ID {conversation_id} not found")
            return JSONResponse(status_code=404, content={"error": "Conversation not found"})

        logger.info(f"Retrieved conversation with ID: {conversation_id}")
        return conversation.get_info()
    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content="Error retrieving conversation")


@router.put("/update/{conversation_id}", summary="更新对话配置")
async def update_conversation(
    conversation_id: int,
    req: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.user_id == str(current_user.id))
        )
        conversation = result.scalar_one_or_none()
        # 检查对话是否存在
        if not conversation:
            logger.error(f"Conversation ID {conversation_id} not found for update")
            return JSONResponse(status_code=404, content={"error": "Conversation not found"})

        # 更新对话名称
        if req.name is not None:
            conversation.name = str(req.name)

        # 更新对话描述
        if req.description is not None:
            conversation.description = str(req.description)

        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        logger.info(f"Updated conversation with ID: {conversation_id}")
        return JSONResponse(content={"message": "conversation updated"})
    except Exception as e:
        logger.error(f"Error updating conversation: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Error updating conversation"})


@router.get("/{conversation_id}/messages", summary="获取对话的所有消息")
async def get_conversation_messages(conversation_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Message).where(Message.conversation_id == conversation_id))
        messages = result.scalars().all()
        logger.info(f"Retrieved {len(messages)} messages for conversation ID: {conversation_id}")

        processed_messages = []
        for message in messages:
            msg_dict = message.get_info()

            charts = msg_dict.get("charts")
            sample_data = msg_dict.get("sample_data")
            code_result = msg_dict.get("code_result")
            if sample_data:
                import json

                msg_dict["sample_data"] = json.loads(sample_data)

            if charts:
                # ✅ charts 可能是 dict / list / json-string，这里全部兼容
                import json

                if isinstance(charts, str):
                    try:
                        charts = json.loads(charts)
                    except Exception as e:
                        logger.error(f"load charts error: {e}")

                # ✅ 如果是单图，处理为列表统一格式
                if isinstance(charts, dict):
                    charts = [charts]

                # ✅ 处理每个图表配置
                try:
                    if code_result:
                        data = json.loads(code_result)
                    else:
                        data = json.loads(msg_dict["sample_data"])
                    chart_options = await generate_chart_tool(
                        data, charts
                    )  # <── 自己的绘图处理函数
                except Exception as e:
                    logger.error(f"Chart generate error: {e}")

                msg_dict["charts"] = chart_options

            processed_messages.append(msg_dict)

        return {"messages": processed_messages}

    except Exception as e:
        logger.error(f"Error retrieving messages for conversation {conversation_id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
