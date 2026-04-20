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
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel, Field

load_dotenv()

from experimental_agent.agent import create_analyst_agent
from experimental_agent.context import AgentContext, DatasourceConfig

app = FastAPI(
    title="VoloData Deep Agent API v2",
    version="0.2.0",
    description="基于 deepagents 的对话式数据分析 Agent，支持 HITL、长期记忆和 Skill 库",
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
    messages: list[ChatMessage] = Field(..., description="对话历史，最后一条应为 user 消息")
    session_id: str | None = Field(None, description="会话 ID（thread_id），多轮对话必须保持一致")
    user_id: str = Field("anonymous", description="用户唯一标识，用于隔离记忆")
    datasource: DatasourceRequest | None = Field(None, description="数据源配置，留空则查询用户已创建的连接")
    hitl_tools: list[str] = Field(
        default_factory=list,
        description="需要 HITL 确认的工具名列表，如 ['execute_sql_query']。留空则不打断任何操作。",
    )
    language: str = Field("zh", description="用户偏好语言：zh / en")


class HITLDecision(BaseModel):
    type: str = Field(..., description="决策类型：approve / edit / reject")
    edited_action: dict | None = Field(None, description="当 type=edit 时，传入修改后的工具名和参数")


class ResumeRequest(BaseModel):
    session_id: str = Field(..., description="需要恢复的会话 ID（必须与原请求一致）")
    decisions: list[HITLDecision] = Field(..., description="针对每个待确认工具调用的决策，顺序需与 interrupt 中 action_requests 一致")


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
    return AgentContext(user_id=req.user_id, datasource=ds, language=req.language)


def _build_lc_messages(messages: list[ChatMessage]) -> list:
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
    ctx = _build_context(req)
    lc_messages = _build_lc_messages(req.messages)
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
    - 编辑：{"type": "edit", "edited_action": {"name": "execute_sql_query", "args": {...}}}
    - 拒绝：{"type": "reject"}
    """
    # resume 必须用同一个 agent 实例（checkpointer 绑定的），
    # 默认用 _default_agent；如果 session 是从 HITL agent 创建的，
    # checkpointer 是共享的，所以 default agent 也能恢复状态。
    agent = _default_agent
    config = {"configurable": {"thread_id": req.session_id}}
    decisions = [d.model_dump(exclude_none=True) for d in req.decisions]

    result = await agent.ainvoke(
        Command(resume={"decisions": decisions}),
        config=config,
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
    ctx = _build_context(req)
    lc_messages = _build_lc_messages(req.messages)
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
        state = await _default_agent.aget_state(config)
        has_interrupt = bool(state.next) and any("interrupt" in str(n).lower() for n in state.next)
        return {
            "session_id": session_id,
            "exists": state is not None,
            "has_pending_interrupt": has_interrupt,
            "message_count": len(state.values.get("messages", [])) if state.values else 0,
            "next_nodes": list(state.next) if state.next else [],
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}")


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
