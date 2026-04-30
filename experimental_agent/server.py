"""
experimental_agent FastAPI 服务 (v2 — 深度优化版)

新增接口：
- POST /agent/chat/resume   — 恢复 HITL 中断的会话（批准/编辑/拒绝工具调用）
- GET  /agent/session/{id}  — 查询会话状态（是否有待处理的 interrupt）

增强：
- ChatRequest 新增 user_id / datasource / hitl_tools 字段
- HITL 默认关闭，通过 hitl_tools 按需启用（只在关键操作打断）
- 所有接口通过 thread_id (session_id) 关联 checkpointer，支持多轮状态持久
- SSE 流式接口额外推送 interrupt 事件，前端可弹出确认框
"""

import json
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel, Field

load_dotenv()

from experimental_agent.agent import create_analyst_agent, ensure_user_memories, init_agent_store
from experimental_agent.context import AgentContext, DatasourceConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 初始化 Redis Store 和 Checkpointer（创建索引、预置记忆文件）
    from experimental_agent.agent import _checkpointer, agent_store
    await _checkpointer.asetup()
    await agent_store.setup()
    await init_agent_store()
    yield


app = FastAPI(
    title="VoloData Deep Agent API v2",
    version="0.2.0",
    description="基于 deepagents 的对话式数据分析 Agent，支持 HITL、长期记忆和 Skill 库",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Agent 缓存 ───────────────────────────────────────────────────────────────
# 无 HITL 的默认实例（绝大多数请求使用此实例，不会打断任何操作）
# 有 HITL 时按 hitl_tools 组合缓存，避免重复创建
_default_agent = create_analyst_agent()
_agent_cache: dict[str, CompiledStateGraph] = {}

# session_id → hitl_tools 映射：确保 get_session_state / resume 时使用正确的 agent 实例
_session_hitl_map: dict[str, list[str]] = {}


def _get_agent(hitl_tools: list[str] | None = None) -> CompiledStateGraph:
    """获取 Agent 实例。无 HITL 时用默认单例；有 HITL 时按工具组合缓存。"""
    if not hitl_tools:
        return _default_agent
    cache_key = ",".join(sorted(hitl_tools))
    if cache_key not in _agent_cache:
        _agent_cache[cache_key] = create_analyst_agent(
            enable_hitl=True,
            hitl_tools=hitl_tools,
        )
    return _agent_cache[cache_key]


# ─── Pydantic Models ──────────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色：user / assistant")
    content: str = Field(..., description="消息内容")


class DatasourceRequest(BaseModel):
    collection_prefix: str = Field("", description="ChromaDB 集合前缀")
    db_params: dict = Field(default_factory=dict, description="数据库连接参数")


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., description="对话消息列表。首轮对话传全部消息；多轮对话（有 session_id）只需传最新一条 user 消息，历史由 checkpointer 维护")
    session_id: str | None = Field(None, description="会话 ID（thread_id），多轮对话必须保持一致")
    user_id: str = Field("anonymous", description="用户唯一标识，用于隔离记忆")
    datasource: DatasourceRequest | None = Field(None, description="数据源配置，留空则查询用户已创建的连接")
    hitl_tools: list[str] = Field(
        default_factory=list,
        description="需要 HITL 确认的工具名列表，如 ['execute_sql']。留空则不打断任何操作。",
    )
    language: str = Field("zh", description="用户偏好语言：zh / en")


class HITLDecision(BaseModel):
    type: str = Field(..., description="决策类型：approve / edit / reject")
    edited_action: dict | None = Field(None, description="当 type=edit 时，传入修改后的工具名和参数")


class ResumeRequest(BaseModel):
    session_id: str = Field(..., description="需要恢复的会话 ID（必须与原请求一致）")
    decisions: list[HITLDecision] = Field(..., description="针对每个待确认工具调用的决策，顺序需与 interrupt 中 action_requests 一致")
    user_id: str = Field("anonymous", description="用户唯一标识，用于构建 context（需与原请求一致）")
    datasource: DatasourceRequest | None = Field(None, description="数据源配置（需与原请求一致）")
    hitl_tools: list[str] = Field(
        default_factory=list,
        description="与原请求一致的 HITL 工具列表，用于匹配正确的 agent 实例",
    )
    language: str = Field("zh", description="语言偏好")


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    tool_calls: list[dict] = []
    interrupted: bool = False
    interrupt_info: dict | None = None


# ─── 工具函数 ──────────────────────────────────────────────────────────────────


def _build_context(req: ChatRequest) -> AgentContext:
    ds = DatasourceConfig()
    if req.datasource:
        ds.collection_prefix = req.datasource.collection_prefix
        ds.db_params = req.datasource.db_params
    question = ""
    for m in reversed(req.messages):
        if m.role == "user" and m.content:
            question = m.content
            break
    return AgentContext(
        user_id=req.user_id, datasource=ds, language=req.language,
        session_id=req.session_id or "", question=question,
    )


def _build_context_from_resume(req: ResumeRequest) -> AgentContext:
    ds = DatasourceConfig()
    if req.datasource:
        ds.collection_prefix = req.datasource.collection_prefix
        ds.db_params = req.datasource.db_params
    return AgentContext(
        user_id=req.user_id, datasource=ds, language=req.language,
        session_id=req.session_id, question="",
    )


def _build_runtime_info(ctx: AgentContext) -> str:
    """构建运行时上下文信息，注入到 system prompt 末尾，替代 get_current_user_info 工具。"""
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


def _build_lc_messages(messages: list[ChatMessage], is_multi_turn: bool = False) -> list:
    """构建 LangChain 消息列表。

    多轮对话（is_multi_turn=True）时，checkpointer 已维护历史，只需传最新一条 user 消息；
    首轮对话时传全部 messages。
    """
    if is_multi_turn and messages:
        # 多轮对话：只取最后一条 user 消息，避免与 checkpointer 历史重复
        for m in reversed(messages):
            if m.role == "user":
                return [HumanMessage(content=m.content)]
        return []
    # 首轮对话：传入全部消息
    lc_msgs = []
    for m in messages:
        if m.role == "user":
            lc_msgs.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_msgs.append(AIMessage(content=m.content))
    return lc_msgs


def _get_skill_files(agent: CompiledStateGraph) -> dict:
    return getattr(agent, "_skill_files", {})


def _extract_interrupt_info(result) -> dict | None:
    if not hasattr(result, "interrupts") or not result.interrupts:
        return None
    interrupt_value = result.interrupts[0].value
    return {
        "action_requests": interrupt_value.get("action_requests", []),
        "review_configs": interrupt_value.get("review_configs", []),
    }


def _extract_answer(result) -> str:
    """从 agent 调用结果中提取最终 AI 回复文本。"""
    msgs = result.get("messages", []) if isinstance(result, dict) else result.value.get("messages", [])
    answer = ""
    for msg in msgs:
        if isinstance(msg, AIMessage) and msg.content:
            answer = msg.content
    return answer


# ─── 接口 ──────────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok", "service": "volo-data-deepagent-v2", "features": ["hitl", "memory", "skills", "context-compression"]}


@app.post("/agent/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    普通对话接口（非流式）。

    - 默认不启用 HITL，Agent 自主完成所有操作
    - 传入 hitl_tools 后，指定工具执行前暂停请求确认
    - 若触发 HITL 中断，返回 interrupted=true 和 interrupt_info
    """
    agent = _get_agent(req.hitl_tools or None)
    session_id = req.session_id or str(uuid.uuid4())
    # 记录 session 使用的 hitl_tools，供 get_session_state / resume 查找正确的 agent 实例
    if req.hitl_tools:
        _session_hitl_map[session_id] = req.hitl_tools
    is_multi_turn = req.session_id is not None  # 有 session_id 说明是多轮对话
    ctx = _build_context(req)
    # 确保用户记忆已初始化（首次对话时从模板预置）
    await ensure_user_memories(ctx.user_id)
    lc_messages = _build_lc_messages(req.messages, is_multi_turn=is_multi_turn)
    # 将运行时上下文信息注入为 SystemMessage，避免 Agent 额外调用 get_current_user_info
    lc_messages.insert(0, SystemMessage(content=_build_runtime_info(ctx)))
    config = {"configurable": {"thread_id": session_id}}

    result = await agent.ainvoke(
        {"messages": lc_messages, "files": _get_skill_files(agent)},
        config=config,
        context=ctx,
        version="v2",
    )

    # 检查 HITL 中断
    interrupt_info = _extract_interrupt_info(result)
    if interrupt_info:
        return ChatResponse(
            session_id=session_id,
            answer="操作需要您的确认，请查看 interrupt_info 并通过 /agent/chat/resume 恢复执行。",
            interrupted=True,
            interrupt_info=interrupt_info,
        )

    # 提取最终回复和工具调用记录
    answer = _extract_answer(result)
    tool_calls_log = []
    msgs = result.get("messages", []) if isinstance(result, dict) else result.value.get("messages", [])
    for msg in msgs:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_log.append({"name": tc["name"], "args": tc["args"]})

    return ChatResponse(session_id=session_id, answer=answer, tool_calls=tool_calls_log)


@app.post("/agent/chat/resume", response_model=ChatResponse)
async def resume_chat(req: ResumeRequest):
    """
    恢复 HITL 中断的会话。

    前端在收到 interrupted=true 后，展示工具调用详情给用户，
    获取用户决策后调用此接口恢复执行。

    决策示例：
    - 批准：{"type": "approve"}
    - 编辑：{"type": "edit", "edited_action": {"name": "execute_sql", "args": {...}}}
    - 拒绝：{"type": "reject"}

    重要：必须传入与原请求一致的 hitl_tools，以匹配正确的 agent 实例。
    同时传入 datasource 等上下文信息，确保恢复后工具能正常执行。
    """
    # 必须用与原请求相同的 HITL agent 实例恢复，否则图结构不匹配
    # 优先从映射查找，回退到请求参数
    hitl_tools = _session_hitl_map.get(req.session_id, req.hitl_tools)
    agent = _get_agent(hitl_tools or None)
    config = {"configurable": {"thread_id": req.session_id}}
    decisions = [d.model_dump(exclude_none=True) for d in req.decisions]

    # 构建 context，确保恢复后工具能读取数据源配置
    ctx = _build_context_from_resume(req)

    result = await agent.ainvoke(
        Command(resume={"decisions": decisions}),
        config=config,
        context=ctx,
        version="v2",
    )

    # 检查是否还有新的中断
    interrupt_info = _extract_interrupt_info(result)
    if interrupt_info:
        return ChatResponse(
            session_id=req.session_id,
            answer="还有操作需要您的确认。",
            interrupted=True,
            interrupt_info=interrupt_info,
        )

    answer = _extract_answer(result)
    return ChatResponse(session_id=req.session_id, answer=answer)


@app.post("/agent/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    SSE 流式对话接口。

    SSE 事件类型：
    - token         — AI 生成的文本片段
    - tool_start    — 工具调用开始（含工具名和参数）
    - tool_result   — 工具执行结果摘要
    - interrupt     — HITL 中断（含 action_requests，前端弹出确认框）
    - done          — 流结束（含 session_id）
    - error         — 发生错误
    """
    agent = _get_agent(req.hitl_tools or None)
    session_id = req.session_id or str(uuid.uuid4())
    # 记录 session 使用的 hitl_tools
    if req.hitl_tools:
        _session_hitl_map[session_id] = req.hitl_tools
    is_multi_turn = req.session_id is not None
    ctx = _build_context(req)
    # 确保用户记忆已初始化（首次对话时从模板预置）
    await ensure_user_memories(ctx.user_id)
    lc_messages = _build_lc_messages(req.messages, is_multi_turn=is_multi_turn)
    lc_messages.insert(0, SystemMessage(content=_build_runtime_info(ctx)))
    config = {"configurable": {"thread_id": session_id}}

    async def event_stream() -> AsyncGenerator[str, None]:
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
                    chunk: AIMessageChunk = data.get("chunk")
                    if chunk and chunk.content:
                        yield _sse("token", {"text": chunk.content})

                elif kind == "on_tool_start":
                    yield _sse("tool_start", {
                        "tool": event.get("name"),
                        "args": data.get("input", {}),
                    })

                elif kind == "on_tool_end":
                    output = data.get("output")
                    if hasattr(output, "content"):
                        result_content = output.content
                    elif isinstance(output, str):
                        result_content = output[:500]
                    else:
                        try:
                            result_content = json.dumps(output, ensure_ascii=False, default=str)[:500]
                        except Exception:
                            result_content = str(output)[:500]
                    yield _sse("tool_result", {"tool": event.get("name"), "result": result_content})

                elif kind == "on_interrupt":
                    interrupt_value = data.get("interrupt", {})
                    yield _sse("interrupt", {
                        "session_id": session_id,
                        "action_requests": interrupt_value.get("action_requests", []),
                        "review_configs": interrupt_value.get("review_configs", []),
                        "message": "操作需要您的确认，请通过 POST /agent/chat/resume 恢复执行",
                    })

            yield _sse("done", {"session_id": session_id})

        except Exception as e:
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/agent/session/{session_id}")
async def get_session_state(session_id: str):
    """查询会话状态：是否有待处理的 HITL interrupt、消息数量等。"""
    try:
        config = {"configurable": {"thread_id": session_id}}
        # 必须使用与创建会话时相同的 agent 实例，否则图结构不同导致 interrupts 检测失败
        hitl_tools = _session_hitl_map.get(session_id)
        agent = _get_agent(hitl_tools)
        state = await agent.aget_state(config)
        has_interrupt = bool(state.interrupts)

        # 兜底：映射中没有记录（如服务重启后）时，尝试所有缓存的 HITL agent 探测中断
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

        # 最终兜底：有 next_nodes 但未检测到 interrupt 时，尝试用常见 HITL 工具组合探测
        if not has_interrupt and state.next:
            for probe_tools in [["execute_sql"], ["generate_sql", "execute_sql"]]:
                try:
                    probe_agent = _get_agent(probe_tools)
                    alt_state = await probe_agent.aget_state(config)
                    if bool(alt_state.interrupts):
                        state = alt_state
                        has_interrupt = True
                        break
                except Exception:
                    continue
        interrupt_details = []
        if has_interrupt:
            for intr in state.interrupts:
                interrupt_details.append({
                    "value": intr.value if hasattr(intr, "value") else str(intr),
                })
        return {
            "session_id": session_id,
            "exists": state is not None,
            "has_pending_interrupt": has_interrupt,
            "interrupts": interrupt_details,
            "message_count": len(state.values.get("messages", [])) if state.values else 0,
            "next_nodes": list(state.next) if state.next else [],
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}")


@app.get("/agent/audit")
async def get_audit_logs(
    user_id: str | None = Query(None, description="按用户 ID 筛选"),
    session_id: str | None = Query(None, description="按会话 ID 筛选"),
    status: str | None = Query(None, description="按状态筛选：success / error / rejected"),
    start_time: str | None = Query(None, description="起始时间 (ISO 8601)"),
    end_time: str | None = Query(None, description="结束时间 (ISO 8601)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """查询 SQL 审计日志，支持按用户、会话、状态、时间范围筛选和分页。"""
    from datetime import datetime as dt

    from sqlalchemy import func as sa_func, select

    from config.database import async_session
    from config.models import SqlAuditLog

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
                count_query = count_query.where(SqlAuditLog.created_at >= dt.fromisoformat(start_time))
            if end_time:
                query = query.where(SqlAuditLog.created_at <= dt.fromisoformat(end_time))
                count_query = count_query.where(SqlAuditLog.created_at <= dt.fromisoformat(end_time))

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


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
