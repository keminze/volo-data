"""
对话式数据分析 Agent (v2 — 深度优化版)

核心能力：
1. 人机交互 (HITL)        — 指定工具执行前可暂停请求用户确认
2. 长期记忆               — 基于 AsyncRedisStore + CompositeBackend 的跨会话记忆
3. Skill 库               — 4 个专业技能：data-analysis / chart-expert / report-writer / sql-optimizer
4. 上下文压缩             — 内置 summarization middleware，自动处理长对话
5. Runtime Context        — AgentContext 传递用户身份和数据源，工具无需明文接收敏感参数
6. Checkpointer           — AsyncRedisSaver 持久化会话状态，支持多轮对话和 HITL resume

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
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.redis import AsyncRedisStore

from experimental_agent.context import AgentContext
from experimental_agent.tools import DATA_ANALYSIS_TOOLS

load_dotenv()

# ─── Redis 连接配置 ──────────────────────────────────────────────────────────────
# Redis Search 索引只能在 db=0 上创建，因此 Agent 专用 db 需为 0
_REDIS_URL = os.getenv("REDIS_AGENT_URL", f"redis://:{os.getenv('REDIS_PASSWORD', '')}@{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0")

# ─── 全局共享 Store（长期记忆，跨会话持久，Redis 存储）─────────────────────────
agent_store = AsyncRedisStore(redis_url=_REDIS_URL)


# ─── Checkpointer（会话状态持久化，Redis 存储）─────────────────────────────────
_checkpointer = AsyncRedisSaver(redis_url=_REDIS_URL)

# ─── 技能文件路径（相对于本文件）─────────────────────────────────────────────
_SKILLS_DIR = pathlib.Path(__file__).parent / "skills"
_MEMORIES_DIR = pathlib.Path(__file__).parent / "memories"

# ─── System Prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """"
你是 VoloData 数据分析助手，专注于商业数据分析、指标查询、结果解释和图表/报告生成。
目标：以最少的工具调用，准确完成用户问题，给出简洁、可信、可复核的结果。

## 角色定位
- 数据分析助手，不是闲聊助手
- 只回答与当前任务相关的内容
- 优先保证结果准确、流程收敛、工具调用克制

## 回复风格
- 直接回答，不冗长开场白
- 使用业务名称，不暴露底层字段名（`user_id` → “用户ID”）
- 数值保留 3 位小数，不自行换算单位
- 简单计算（分↔元、百分比、加减乘除）直接在回复里算，不调用工具
- 数据为空时，30字内简短说明

## SQL 工具规则（核心约束）

### 必须遵守
1. 先想清楚再调用：我需要什么数据？能否一次查完？
2. 一次 `generate_sql` + `execute_sql` 查出所有需要的指标，不分多次
3. `execute_sql` 只执行 `generate_sql` 输出的 SQL，不做任何修改
4. 如果 SQL 执行失败，重新调用 `generate_sql`（传入错误信息），最多重试 1 次

### 辅助工具（按需使用，调用后必须继续主流程）
- `get_ddl`：获取相关表结构。如果对表结构不熟悉，先调用此工具
- `get_question_sql`：获取相似的历史问题-SQL对。如果需要参考历史查询，调用此工具
- 调用 `get_ddl` 或 `get_question_sql` 后，**必须**将结果作为 `generate_sql` 的 `ddl_list` / `question_sql_list` 参数传入，然后继续执行 SQL
- **禁止**在调用辅助工具后直接回复用户——它们只是准备步骤，不是最终答案

### 严禁
- 手动编写、修改、微调 SQL（哪怕”看起来更合理”）
- 为同一问题反复查询（先查时间范围、再查明细、再查汇总）
- 主动查询用户未要求的衍生指标
- 连续 3 次及以上调用 SQL 工具
- 用多次 SQL 分段凑答案
- 调用 get_ddl / get_question_sql 后直接回复用户（必须继续调用 generate_sql）

## 计算工具规则
- 简单计算（单位换算、百分比、加减乘除）直接在回复里做
- 只有复杂计算（同比、环比、窗口分析、分组后二次聚合）才用 `generate_compute_code` + `run_compute`

## 图表与报告
- 用户要求可视化时，调用 `generate_charts`
- 用户要求分析结论/解读时，调用 `generate_analysis_report`
- 用户只问一个指标时，不主动生成图表或报告

## 决策边界
- 只做用户明确要求的事情，不主动扩展分析范围
- 不主动生成额外月份、维度、对比
- 结果足以回答问题时，立即停止工具调用

## 记忆管理
- 仅当用户明确说”记住””保存偏好”时，调用 `save_user_preference`
- 不主动修改记忆，不保存临时任务信息

## HITL / 人工确认
- 出现确认请求时，展示工具名称、参数、可选操作（approve / edit / reject）
- 只读查询默认不触发确认
- 未经确认，不得执行写入、删除等高风险操作

## 执行流程（严格按顺序，不可跳过步骤 3~5）
1. 理解用户问题
2. 如需了解表结构，调用 `get_ddl`；如需参考历史查询，调用 `get_question_sql`
3. **必须**调用 `generate_sql`（可将步骤2的结果作为 ddl_list / question_sql_list 传入）
4. **必须**调用 `audit_sql` 对生成的 SQL 进行审计记录
5. **必须**调用 `execute_sql` 执行 SQL（若未审计，execute_sql 将拒绝执行）
6. 如需复杂计算，调用 `generate_compute_code` + `run_compute`
7. 如需图表/报告，调用 `generate_charts` / `generate_analysis_report`
8. 返回结果
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


async def _seed_store_with_memories(store: AsyncRedisStore, namespace: tuple) -> None:
    """将本地记忆模板文件预置到 Store 中（仅在 namespace 尚无数据时）。"""
    for mem_file in _MEMORIES_DIR.glob("*.md"):
        virtual_path = f"/memories/{mem_file.name}"
        existing = await store.aget(namespace, virtual_path)
        if existing is None:
            await store.aput(
                namespace,
                virtual_path,
                create_file_data(mem_file.read_text(encoding="utf-8")),
            )


async def ensure_user_memories(user_id: str, agent_namespace: str = "volo-analyst") -> None:
    """确保指定用户的记忆文件已初始化。如果用户首次使用，从模板预置一份。

    在每次对话开始时调用，保证新用户也有 AGENTS.md 模板。
    """
    namespace = (agent_namespace, user_id)
    existing = await agent_store.aget(namespace, "/memories/AGENTS.md")
    if existing is None:
        await _seed_store_with_memories(agent_store, namespace)


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
            示例：["execute_sql"] 会在每次执行 SQL 前请求确认。
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

    # ── 2. 预置记忆文件到 Store（异步，需在 lifespan 中调用 init_agent_store）─────

    # ── 3. 构建 Backend（CompositeBackend：/memories/ → Store，其余 → State）
    def _make_backend(rt=None):
        """工厂函数，支持带/不带 runtime 的调用。
        namespace 按 (agent_namespace, user_id) 隔离，每个用户拥有独立记忆空间。
        """
        def _user_namespace(rt) -> tuple:
            user_id = "anonymous"
            if rt is not None and hasattr(rt, "context") and rt.context is not None:
                user_id = getattr(rt.context, "user_id", "anonymous")
            return (agent_namespace, user_id)

        if rt is not None:
            return CompositeBackend(
                default=StateBackend(rt),
                routes={
                    "/memories/": StoreBackend(
                        rt,
                        namespace=_user_namespace,
                    ),
                },
            )
        else:
            return CompositeBackend(
                default=StateBackend(),
                routes={
                    "/memories/": StoreBackend(
                        namespace=_user_namespace,
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


# ─── 异步初始化（在 FastAPI lifespan 中调用）─────────────────────────────────────

async def init_agent_store(namespace: str = "volo-analyst") -> None:
    """初始化 Agent Store：为默认用户预置记忆模板到 Redis。

    必须在 FastAPI lifespan 的 startup 阶段调用，因为 AsyncRedisStore 要求异步操作。
    每个真实用户首次对话时，会通过 ensure_user_memories 自动初始化。
    """
    await _seed_store_with_memories(agent_store, (namespace, "anonymous"))
