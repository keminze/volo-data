"""
BI Agent 路由 — 对话式数据分析 Agent

从 experimental_agent 合并到主服务架构，集成 JWT 认证、Conversation/Message 持久化。
"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config.database import AsyncSession, async_session, get_db
from config.models import Conversation, DBConnection, Message, ToolCall
from config.parameter import AgentChatRequest, AgentResumeRequest
from dependencies import get_current_user
from experimental_agent.agent import create_analyst_agent, ensure_user_memories
from experimental_agent.context import AgentContext, DatasourceConfig
from redis_client import redis_client
from services.auth import User

router = APIRouter()

# ─── 模块级状态 ────────────────────────────────────────────────────────────────

_REDIS_HITL_KEY = "session_hitl_map"

_default_agent: CompiledStateGraph | None = None
_agent_cache: dict[str, CompiledStateGraph] = {}
_session_hitl_map: dict[str, list[str]] = {}


# ─── 初始化函数（在 main.py lifespan 中调用）──────────────────────────────────


async def init_agent_resources():
    """初始化 Agent Store/Checkpointer/记忆，默认 Agent 实例。"""
    global _default_agent, _session_hitl_map
    import experimental_agent.agent as agent_module

    # 先在 async 上下文中创建 Store 和 Checkpointer
    await agent_module.init_store_and_checkpointer()

    await agent_module._checkpointer.asetup()
    await agent_module.agent_store.setup()
    await agent_module.init_agent_store()
    _default_agent = create_analyst_agent()
    _session_hitl_map = await _load_session_hitl_map()


# ─── HITL 映射持久化 ──────────────────────────────────────────────────────────


async def _load_session_hitl_map() -> dict[str, list[str]]:
    try:
        raw = await redis_client.hgetall(_REDIS_HITL_KEY)
        return {k.decode() if isinstance(k, bytes) else k: json.loads(v) for k, v in raw.items()}
    except Exception:
        return {}


async def _save_session_hitl_map(session_id: str, hitl_tools: list[str]) -> None:
    try:
        await redis_client.hset(
            _REDIS_HITL_KEY,
            session_id,
            json.dumps(hitl_tools, ensure_ascii=False),
        )
    except Exception:
        pass


# ─── 辅助函数 ──────────────────────────────────────────────────────────────────


def _get_agent(hitl_tools: list[str] | None = None) -> CompiledStateGraph:
    if not hitl_tools:
        return _default_agent
    cache_key = ",".join(sorted(hitl_tools))
    if cache_key not in _agent_cache:
        _agent_cache[cache_key] = create_analyst_agent(
            enable_hitl=True,
            hitl_tools=hitl_tools,
        )
    return _agent_cache[cache_key]


def _get_skill_files(agent: CompiledStateGraph) -> dict:
    return getattr(agent, "_skill_files", {})


async def _get_user_conversation(
    conversation_id: int, user_id: int, db: AsyncSession
) -> Conversation:
    """查询对话并验证归属，同时加载 db_connection 关系。"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == str(user_id))
        .options(selectinload(Conversation.db_connection))
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在或无权限")
    if conversation.connection_id is None:
        raise HTTPException(status_code=400, detail="对话未关联数据源连接")
    return conversation


def _build_context(
    user_id: str,
    conversation: Conversation,
    language: str,
    question: str,
) -> AgentContext:
    ds = DatasourceConfig()
    if conversation.db_connection:
        conn = conversation.db_connection
        ds.collection_prefix = conn.collection_prefix or ""
        ds.db_params = conn.get_db_info()
    return AgentContext(
        user_id=str(user_id),
        datasource=ds,
        language=language,
        session_id=str(conversation.id),
        question=question,
    )


def _build_runtime_info(ctx: AgentContext) -> str:
    lines = [
        "\n## 当前请求上下文（系统自动注入，无需调用工具）",
        f"- 用户 ID：{ctx.user_id}",
        f"- 语言偏好：{ctx.language}",
        f"- 数据源已配置：{'是' if ctx.datasource.collection_prefix and ctx.datasource.db_params else '否'}",
    ]
    if ctx.datasource.collection_prefix:
        lines.append(f"- 数据源 collection_prefix：{ctx.datasource.collection_prefix}")
    if ctx.datasource.db_params:
        lines.append(f"- 数据库类型：{ctx.datasource.db_params.get('db_type', 'unknown')}")
    return "\n".join(lines)


def _build_lc_messages(input_text: str, is_multi_turn: bool = False) -> list:
    """构建 LangChain 消息列表。

    多轮对话时 checkpointer 已维护历史，只传最新一条 user 消息；
    首轮时只传 input_text。
    """
    return [HumanMessage(content=input_text)]


def _extract_interrupt_info(result) -> dict | None:
    if not hasattr(result, "interrupts") or not result.interrupts:
        return None
    interrupt_value = result.interrupts[0].value
    return {
        "action_requests": interrupt_value.get("action_requests", []),
        "review_configs": interrupt_value.get("review_configs", []),
    }


def _extract_answer(result) -> str:
    msgs = (
        result.get("messages", []) if isinstance(result, dict) else result.value.get("messages", [])
    )
    answer = ""
    for msg in msgs:
        if isinstance(msg, AIMessage) and msg.content:
            answer = msg.content
    return _strip_tool_json(answer)


# ─── 工具 JSON 清理 ────────────────────────────────────────────────────────────

_TOOL_JSON_KEYS = {
    "need_chart",
    "need_charts",
    "chart_type",
    "x_col",
    "y_col",
    "category_col",
    "stacked",
}


def _strip_tool_json(text: str) -> str:
    """剥离文本中 LLM 混入的工具调用 JSON（如 generate_charts 的参数）。"""
    import re

    def _should_strip(match: str) -> bool:
        return any(f'"{k}"' in match for k in _TOOL_JSON_KEYS)

    result = re.sub(r"\{[^{}]*\}", lambda m: "" if _should_strip(m.group()) else m.group(), text)
    result = re.sub(
        r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}",
        lambda m: "" if _should_strip(m.group()) else m.group(),
        result,
    )
    return re.sub(r"\n{3,}", "\n\n", result).strip()


def _extract_current_turn_tool_calls(result) -> list[dict]:
    """仅提取本轮对话的工具调用及结果（最后一条 HumanMessage 之后的）。"""
    msgs = (
        result.get("messages", []) if isinstance(result, dict) else result.value.get("messages", [])
    )
    # 找到最后一条 HumanMessage 的位置
    last_human_idx = -1
    for i, msg in enumerate(msgs):
        if isinstance(msg, HumanMessage):
            last_human_idx = i
    turn_msgs = msgs[last_human_idx + 1 :]

    # 先收集所有 ToolMessage，用 tool_call_id 建索引
    tool_results: dict[str, str] = {}
    for msg in turn_msgs:
        if isinstance(msg, ToolMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            tool_results[msg.tool_call_id] = content[:1000]

    # 收集 AIMessage 的工具调用，并匹配结果
    tool_calls_log = []
    for msg in turn_msgs:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                entry = {"name": tc["name"], "args": tc["args"]}
                tc_id = tc.get("id")
                if tc_id and tc_id in tool_results:
                    entry["result"] = tool_results[tc_id]
                tool_calls_log.append(entry)
    return tool_calls_log


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


async def _save_messages(
    conversation_id: int, user_input: str, answer: str, tool_calls: list | None = None
):
    """保存用户消息和 AI 回复到 Message 表，工具调用记录保存到 ToolCall 表。"""
    try:
        async with async_session() as db:
            db.add(Message(conversation_id=conversation_id, role="user", content=user_input))
            ai_msg = Message(conversation_id=conversation_id, role="ai", content=answer)
            db.add(ai_msg)
            await db.flush()  # 获取 ai_msg.id

            if tool_calls:
                tc_ids = []
                for tc in tool_calls:
                    record = ToolCall(
                        message_id=ai_msg.id,
                        tool_name=tc["name"],
                        tool_args=tc.get("args"),
                        tool_result=tc.get("result"),
                    )
                    db.add(record)
                    await db.flush()
                    tc_ids.append(record.id)
                ai_msg.tool_calls = tc_ids

            await db.commit()
    except Exception:
        pass


# ─── 响应模型 ──────────────────────────────────────────────────────────────────


class AgentChatResponse(BaseModel):
    conversation_id: int
    answer: str
    tool_calls: list[dict] = []
    interrupted: bool = False
    interrupt_info: dict | None = None


# ─── 接口 ──────────────────────────────────────────────────────────────────────


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    req: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """非流式对话接口。"""
    conversation = await _get_user_conversation(req.conversation_id, current_user.id, db)
    session_id = str(conversation.id)
    is_multi_turn = session_id in _session_hitl_map or await _session_exists(session_id)

    # 记录 HITL 映射
    if req.hitl_tools:
        _session_hitl_map[session_id] = req.hitl_tools
        await _save_session_hitl_map(session_id, req.hitl_tools)

    ctx = _build_context(current_user.id, conversation, req.language, req.input)
    await ensure_user_memories(ctx.user_id)

    agent = _get_agent(req.hitl_tools or None)
    lc_messages = _build_lc_messages(req.input, is_multi_turn=is_multi_turn)
    lc_messages.insert(0, SystemMessage(content=_build_runtime_info(ctx)))
    config = {"configurable": {"thread_id": session_id}}

    result = await agent.ainvoke(
        {"messages": lc_messages, "files": _get_skill_files(agent)},
        config=config,
        context=ctx,
        version="v2",
    )

    # HITL 中断
    interrupt_info = _extract_interrupt_info(result)
    if interrupt_info:
        return AgentChatResponse(
            conversation_id=conversation.id,
            answer="操作需要您的确认，请查看 interrupt_info 并通过 /agent/chat/resume 恢复执行。",
            interrupted=True,
            interrupt_info=interrupt_info,
        )

    answer = _extract_answer(result)
    tool_calls_log = _extract_current_turn_tool_calls(result)

    await _save_messages(conversation.id, req.input, answer, tool_calls=tool_calls_log)

    return AgentChatResponse(
        conversation_id=conversation.id,
        answer=answer,
        tool_calls=tool_calls_log,
    )


@router.post("/chat/stream")
async def agent_chat_stream(
    req: AgentChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE 流式对话接口。

    SSE 事件类型：token / tool_start / tool_result / interrupt / done / error
    """
    conversation = await _get_user_conversation(req.conversation_id, current_user.id, db)
    session_id = str(conversation.id)
    is_multi_turn = session_id in _session_hitl_map or await _session_exists(session_id)

    if req.hitl_tools:
        _session_hitl_map[session_id] = req.hitl_tools
        await _save_session_hitl_map(session_id, req.hitl_tools)

    ctx = _build_context(current_user.id, conversation, req.language, req.input)
    await ensure_user_memories(ctx.user_id)

    agent = _get_agent(req.hitl_tools or None)
    lc_messages = _build_lc_messages(req.input, is_multi_turn=is_multi_turn)
    lc_messages.insert(0, SystemMessage(content=_build_runtime_info(ctx)))
    config = {"configurable": {"thread_id": session_id}}

    collected_answer = []
    collected_tool_calls: list[dict] = []
    _pending_tool: dict | None = None
    _in_tool_call = False  # 标记是否在工具调用期间，期间跳过 token 发送

    async def event_stream() -> AsyncGenerator[str, None]:
        nonlocal _pending_tool, _in_tool_call
        try:
            async for event in agent.astream_events(
                {"messages": lc_messages, "files": _get_skill_files(agent)},
                config=config,
                context=ctx,
                version="v2",
            ):
                kind = event.get("event")
                data = event.get("data", {})

                if kind == "on_chat_model_stream":
                    # 工具调用期间的 token 是 LLM 的内部思考（含 JSON 参数），跳过
                    if _in_tool_call:
                        continue
                    chunk: AIMessageChunk = data.get("chunk")
                    if chunk and chunk.content:
                        collected_answer.append(chunk.content)
                        yield _sse("token", {"text": chunk.content})

                elif kind == "on_tool_start":
                    _in_tool_call = True
                    _pending_tool = {
                        "name": event.get("name"),
                        "args": data.get("input", {}),
                    }
                    yield _sse(
                        "tool_start",
                        {
                            "tool": _pending_tool["name"],
                            "args": _pending_tool["args"],
                        },
                    )

                elif kind == "on_tool_end":
                    _in_tool_call = False
                    output = data.get("output")
                    if hasattr(output, "content"):
                        result_content = output.content
                    elif isinstance(output, str):
                        result_content = output[:500]
                    else:
                        try:
                            result_content = json.dumps(output, ensure_ascii=False, default=str)[
                                :500
                            ]
                        except Exception:
                            result_content = str(output)[:500]
                    if _pending_tool is not None:
                        _pending_tool["result"] = result_content
                        collected_tool_calls.append(_pending_tool)
                        _pending_tool = None

                elif kind == "on_interrupt":
                    interrupt_value = data.get("interrupt", {})
                    yield _sse(
                        "interrupt",
                        {
                            "session_id": session_id,
                            "action_requests": interrupt_value.get("action_requests", []),
                            "review_configs": interrupt_value.get("review_configs", []),
                            "message": "操作需要您的确认，请通过 POST /agent/chat/resume 恢复执行",
                        },
                    )

            yield _sse("done", {"session_id": session_id})

            # 流结束后保存消息（含工具调用记录）
            full_answer = _strip_tool_json("".join(collected_answer))
            if full_answer:
                background_tasks.add_task(
                    _save_messages,
                    conversation.id,
                    req.input,
                    full_answer,
                    tool_calls=collected_tool_calls or None,
                )

        except Exception as e:
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/resume", response_model=AgentChatResponse)
async def agent_chat_resume(
    req: AgentResumeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """恢复 HITL 中断的会话。"""
    conversation = await _get_user_conversation(req.conversation_id, current_user.id, db)
    session_id = str(conversation.id)

    hitl_tools = _session_hitl_map.get(session_id, [])
    agent = _get_agent(hitl_tools or None)
    config = {"configurable": {"thread_id": session_id}}
    decisions = req.decisions

    ctx = _build_context(current_user.id, conversation, "zh", "")

    result = await agent.ainvoke(
        Command(resume={"decisions": decisions}),
        config=config,
        context=ctx,
        version="v2",
    )

    interrupt_info = _extract_interrupt_info(result)
    if interrupt_info:
        return AgentChatResponse(
            conversation_id=conversation.id,
            answer="还有操作需要您的确认。",
            interrupted=True,
            interrupt_info=interrupt_info,
        )

    answer = _extract_answer(result)
    tool_calls_log = _extract_current_turn_tool_calls(result)
    await _save_messages(conversation.id, "[HITL Resume]", answer, tool_calls=tool_calls_log)

    return AgentChatResponse(
        conversation_id=conversation.id, answer=answer, tool_calls=tool_calls_log
    )


@router.get("/session/{conversation_id}")
async def get_session_state(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询会话状态：是否有待处理的 HITL interrupt。"""
    conversation = await _get_user_conversation(conversation_id, current_user.id, db)
    session_id = str(conversation.id)

    try:
        config = {"configurable": {"thread_id": session_id}}
        hitl_tools = _session_hitl_map.get(session_id)
        agent = _get_agent(hitl_tools)
        state = await agent.aget_state(config)
        has_interrupt = bool(state.interrupts)

        # 兜底：尝试所有缓存的 HITL agent 探测中断
        if not has_interrupt and _agent_cache:
            for cached_agent in _agent_cache.values():
                try:
                    alt_state = await cached_agent.aget_state(config)
                    if bool(alt_state.interrupts):
                        state = alt_state
                        has_interrupt = True
                        break
                except Exception:
                    continue

        interrupt_details = []
        if has_interrupt:
            for intr in state.interrupts:
                interrupt_details.append(
                    {
                        "value": intr.value if hasattr(intr, "value") else str(intr),
                    }
                )

        return {
            "session_id": session_id,
            "conversation_id": conversation_id,
            "has_pending_interrupt": has_interrupt,
            "interrupts": interrupt_details,
            "message_count": len(state.values.get("messages", [])) if state.values else 0,
            "next_nodes": list(state.next) if state.next else [],
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}")


@router.get("/audit")
async def get_audit_logs(
    user_id: str | None = Query(None, description="按用户 ID 筛选"),
    session_id: str | None = Query(None, description="按会话 ID 筛选"),
    status: str | None = Query(None, description="按状态筛选：success / error / rejected"),
    start_time: str | None = Query(None, description="起始时间 (ISO 8601)"),
    end_time: str | None = Query(None, description="结束时间 (ISO 8601)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """查询 SQL 审计日志，支持筛选和分页。非 admin 只能查自己的记录。"""
    from datetime import datetime as dt

    from sqlalchemy import func as sa_func, select

    from config.models import SqlAuditLog

    # 非 admin 只能查自己的审计记录
    if not current_user.is_superuser:
        user_id = str(current_user.id)

    try:
        async with async_session() as db:
            query = select(SqlAuditLog)
            count_query = select(sa_func.count(SqlAuditLog.id))

            if user_id:
                query = query.where(SqlAuditLog.user_id == user_id)
                count_query = count_query.where(SqlAuditLog.user_id == user_id)
            if session_id:
                query = query.where(SqlAuditLog.session_id == session_id)
                count_query = count_query.where(SqlAuditLog.session_id == session_id)
            if status:
                query = query.where(SqlAuditLog.status == status)
                count_query = count_query.where(SqlAuditLog.status == status)
            if start_time:
                query = query.where(SqlAuditLog.created_at >= dt.fromisoformat(start_time))
                count_query = count_query.where(
                    SqlAuditLog.created_at >= dt.fromisoformat(start_time)
                )
            if end_time:
                query = query.where(SqlAuditLog.created_at <= dt.fromisoformat(end_time))
                count_query = count_query.where(
                    SqlAuditLog.created_at <= dt.fromisoformat(end_time)
                )

            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0

            query = query.order_by(SqlAuditLog.created_at.desc()).limit(limit).offset(offset)
            result = await db.execute(query)
            rows = result.scalars().all()

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "records": [
                    {
                        "id": r.id,
                        "user_id": r.user_id,
                        "session_id": r.session_id,
                        "question": r.question,
                        "sql": r.sql,
                        "status": r.status,
                        "row_count": r.row_count,
                        "error_message": r.error_message,
                        "execution_ms": r.execution_ms,
                        "datasource": r.datasource,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in rows
                ],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询审计日志失败: {e}")


# ─── 内部辅助 ──────────────────────────────────────────────────────────────────


async def _session_exists(session_id: str) -> bool:
    """检查 checkpointer 中是否存在该 session。"""
    try:
        config = {"configurable": {"thread_id": session_id}}
        state = await _default_agent.aget_state(config)
        return state is not None and state.values is not None
    except Exception:
        return False
