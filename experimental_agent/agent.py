"""
对话式数据分析 Agent (v2 — 深度优化版)

新增能力：
1. 人机交互 (HITL)        — execute_sql_query 执行前可暂停请求用户确认
2. 长期记忆               — 基于 InMemoryStore + CompositeBackend 的跨会话记忆
3. Skill 库               — 4 个专业技能：data-analysis / chart-expert / report-writer / sql-optimizer
4. 上下文压缩             — 内置 summarization middleware，自动处理长对话
5. Runtime Context        — AgentContext 传递用户身份和数据源，工具无需明文接收敏感参数
6. Checkpointer           — MemorySaver 持久化会话状态，支持 HITL resume

使用方式：
    from experimental_agent.agent import create_analyst_agent, agent_store
    agent = create_analyst_agent()

    # 普通调用
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "查询最近30天销售额"}]},
        config={"configurable": {"thread_id": "session-abc"}},
        context=AgentContext(user_id="u1", datasource=DatasourceConfig(...)),
    )

    # HITL 调用（检测 interrupt 并处理）
    if result.interrupts:
        # 展示给用户，获取决策后 resume
        result = await agent.ainvoke(
            Command(resume={"decisions": [{"type": "approve"}]}),
            config=config,
        )
"""

import os
import pathlib

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data
from deepagents.middleware.summarization import create_summarization_tool_middleware
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.memory import InMemoryStore

from experimental_agent.context import AgentContext
from experimental_agent.tools import DATA_ANALYSIS_TOOLS

load_dotenv()

# ─── 全局共享 Store（长期记忆，跨会话持久）────────────────────────────────────
# 生产环境替换为 PostgresStore / RedisStore 等持久化 Store
agent_store = InMemoryStore()

# ─── Checkpointer（会话状态持久化，HITL 必须）────────────────────────────────
_checkpointer = MemorySaver()

# ─── 技能文件路径（相对于本文件）─────────────────────────────────────────────
_SKILLS_DIR = pathlib.Path(__file__).parent / "skills"
_MEMORIES_DIR = pathlib.Path(__file__).parent / "memories"

# ─── System Prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """你是 VoloData 数据分析助手，专业且友善的商业数据分析专家。

## 核心原则
- 直接回答，不加冗余开场白
- 数值保留 3 位小数，不自行换算单位
- 字段名使用业务名称（如"用户ID"而非`user_id`）
- 数据为空时简短告知（30字内）

## 运行时上下文
你通过 `get_current_user_info` 工具可以获得：
- 当前用户 ID（用于隔离记忆）
- 数据源配置（无需用户每次手动传入）

## 记忆管理
- 用户说"记住..."时，调用 `save_user_preference` 工具，再用内置 `edit_file` 更新记忆文件
- 每次对话开始时，回顾记忆文件中的用户偏好并主动应用
- 跨会话记忆持久保存在 /memories/ 路径下

## 人机交互说明
部分敏感工具（如写操作、删除、批量变更）在执行前可能会暂停，请求用户确认。
如果出现确认请求，请将工具名称和参数展示给用户，让用户决定：
- 批准（approve）：按原参数执行
- 编辑（edit）：修改参数后执行
- 拒绝（reject）：取消此次操作
注意：普通只读查询不会触发确认，只有在配置了 HITL 的工具上才会暂停。
"""

# ─── 技能文件加载 ─────────────────────────────────────────────────────────────


def _load_skill_files() -> dict[str, bytes]:
    """从本地 skills/ 目录加载所有 SKILL.md 文件，转为 StateBackend 所需格式。"""
    files: dict[str, bytes] = {}
    if not _SKILLS_DIR.exists():
        return files
    for skill_file in _SKILLS_DIR.glob("*/SKILL.md"):
        # 虚拟路径格式：/skills/<skill-name>/SKILL.md
        virtual_path = f"/skills/{skill_file.parent.name}/SKILL.md"
        files[virtual_path] = create_file_data(skill_file.read_text(encoding="utf-8"))
    return files


def _load_memory_files() -> dict[str, bytes]:
    """从本地 memories/ 目录加载所有记忆文件，预置到 Store 中。"""
    files: dict[str, bytes] = {}
    if not _MEMORIES_DIR.exists():
        return files
    for mem_file in _MEMORIES_DIR.glob("*.md"):
        virtual_path = f"/memories/{mem_file.name}"
        files[virtual_path] = create_file_data(mem_file.read_text(encoding="utf-8"))
    return files


def _seed_store_with_memories(store: InMemoryStore, namespace: tuple) -> None:
    """将本地记忆文件预置到 Store 中（仅在 namespace 尚无数据时）。"""
    for mem_file in _MEMORIES_DIR.glob("*.md"):
        virtual_path = f"/memories/{mem_file.name}"
        existing = store.get(namespace, virtual_path)
        if existing is None:
            store.put(
                namespace,
                virtual_path,
                create_file_data(mem_file.read_text(encoding="utf-8")),
            )


# ─── Agent 工厂函数 ───────────────────────────────────────────────────────────


def create_analyst_agent(
    model: str | None = None,
    system_prompt: str | None = None,
    enable_hitl: bool = False,
    hitl_tools: list[str] | None = None,
    agent_namespace: str = "volo-analyst",
) -> CompiledStateGraph:
    """
    创建深度优化的数据分析 Agent。

    Args:
        model: 模型标识，格式 'provider:model_name'，默认从环境变量读取。
        system_prompt: 额外的系统提示词，拼接在默认 prompt 前面。
        enable_hitl: 是否启用人机交互。默认关闭，仅在明确配置 hitl_tools 时生效。
        hitl_tools: 需要 HITL 确认的工具名列表。默认空（不阻断任何操作）。
            示例：["execute_sql_query"] 会在每次执行 SQL 前请求确认。
            建议：只在涉及写操作/删除/批量操作时才启用 HITL，
            普通只读查询不应阻断。
        agent_namespace: Store 命名空间，用于隔离不同 Agent 实例的记忆。

    Returns:
        编译好的 deepagents CompiledStateGraph。
    """
    # ── 1. 解析模型 ─────────────────────────────────────────────────────────
    if model is None:
        openai_model = os.getenv("OPENAI_MODEL")
        if openai_model:
            resolved_model = ChatOpenAI(
                model_name=openai_model,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base=os.getenv("OPENAI_BASE_URL"),
            )
        else:
            resolved_model = None  # 回退到 deepagents 默认 Claude 模型
    else:
        resolved_model = model

    # ── 2. 预置记忆文件到 Store ──────────────────────────────────────────────
    _seed_store_with_memories(agent_store, (agent_namespace,))

    # ── 3. 构建 Backend（CompositeBackend：/memories/ → Store，其余 → State）
    def _make_backend(rt=None):
        """工厂函数，支持带/不带 runtime 的调用。"""
        if rt is not None:
            return CompositeBackend(
                default=StateBackend(rt),
                routes={
                    "/memories/": StoreBackend(
                        rt,
                        namespace=lambda _rt: (agent_namespace,),
                    ),
                },
            )
        else:
            return CompositeBackend(
                default=StateBackend(),
                routes={
                    "/memories/": StoreBackend(
                        namespace=lambda _rt: (agent_namespace,),
                    ),
                },
            )

    # ── 4. 加载技能文件（StateBackend 通过 invoke files 参数注入）
    skill_files = _load_skill_files()

    # ── 5. HITL 配置（按需对指定工具设置中断，默认不阻断任何操作）
    # 数据分析 Agent 的核心操作是只读查询，不需要打断；
    # 只有涉及写操作/删除/高风险批量操作时才启用 HITL 确认。
    interrupt_config = None
    if enable_hitl and hitl_tools:
        interrupt_config = {}
        for tool_name in hitl_tools:
            interrupt_config[tool_name] = {
                "allowed_decisions": ["approve", "edit", "reject"],
            }

    # ── 6. 合并 System Prompt ────────────────────────────────────────────────
    final_prompt = (system_prompt + "\n\n" if system_prompt else "") + SYSTEM_PROMPT

    # ── 7. 构建 Agent ────────────────────────────────────────────────────────
    agent = create_deep_agent(
        model=resolved_model,
        tools=DATA_ANALYSIS_TOOLS,
        system_prompt=final_prompt,
        context_schema=AgentContext,
        # Skill 库：progressive disclosure，只有相关时才加载完整内容
        skills=["/skills/"],
        # 长期记忆：每次对话开始自动注入到 system prompt
        memory=["/memories/AGENTS.md"],
        # 后端：/memories/ 持久化到 Store
        backend=_make_backend,
        store=agent_store,
        # HITL：仅在 hitl_tools 中的工具执行前暂停确认（默认空，不阻断）
        interrupt_on=interrupt_config,
        # Checkpointer：持久化会话状态（HITL resume 必须）
        checkpointer=_checkpointer,
        name="volo-data-analyst-v2",
    )

    # ── 8. 绑定技能文件（通过 with_config 预设 invoke files）──────────────────
    # 注：skill_files 通过每次 invoke 时的 files 参数传入（见 server.py）
    agent._skill_files = skill_files  # 挂载到 agent 对象，供 server.py 读取

    return agent
