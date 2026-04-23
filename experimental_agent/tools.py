"""
数据分析 Agent 工具集

工具通过 ToolRuntime[AgentContext] 读取用户身份和数据源配置，无需在消息体中传递敏感参数。
核心工具：generate_sql / execute_sql / generate_compute_code / run_compute / generate_charts / generate_analysis_report
"""

import datetime
import json
import os
import re
from typing import Annotated

import pandas as pd
from dotenv import load_dotenv
from langchain.tools import ToolRuntime
from langchain_core.tools import tool

load_dotenv()

# ─── LLM ──────────────────────────────────────────────────────────────────────
from langchain_openai import ChatOpenAI

_llm = ChatOpenAI(
    model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_BASE_URL"),
)

# ─── 项目内部服务 ───────────────────────────────────────────────────────────────
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.concurrency import run_in_threadpool
from langchain_core.prompts import ChatPromptTemplate
from langchain_sandbox import SyncPyodideSandbox

from services.db import CollectionSuffix, chromadb_client, connect_to_database
from services.prompt import Charts_Decision_Prompt, Code_Decision_Prompt, Generate_Report_Prompt
from services.tools import fix_json_string, generate_echarts_option
from services.vanna_service import Vanna

from experimental_agent.context import AgentContext

_sync_sandbox = SyncPyodideSandbox(allow_net=True, allow_read=True, allow_write=True)

# ─── Vanna 实例缓存 ──────────────────────────────────────────────────────────────
_vanna_cache: dict[str, Vanna] = {}


def _get_vanna(collection_prefix: str, db_params: dict) -> Vanna:
    """获取或创建 Vanna 实例（基于 prefix + db_params 组合缓存）。"""
    cache_key = f"{collection_prefix}:{db_params.get('db_type', '')}:{db_params.get('host', '')}:{db_params.get('database', '')}"
    if cache_key not in _vanna_cache:
        vn = Vanna(
            {
                "client": chromadb_client,
                "documentation_collection_name": f"{collection_prefix}_{CollectionSuffix.DOCUMENTATION.value}",
                "ddl_collection_name": f"{collection_prefix}_{CollectionSuffix.DDL.value}",
                "sql_collection_name": f"{collection_prefix}_{CollectionSuffix.SQL.value}",
            }
        )
        connect_to_database(vn, db_params=db_params)
        _vanna_cache[cache_key] = vn
    return _vanna_cache[cache_key]


# ─── 核心数据分析工具 ──────────────────────────────────────────────────────────


@tool(parse_docstring=True)
async def generate_sql(
    user_question: Annotated[str, "用户的自然语言问题，务必明确说明所有需要查询的指标（例如：'查询最近30天销售额、9月整月销售额、历史总额'）"],
    runtime: ToolRuntime[AgentContext],
    collection_prefix: Annotated[str, "ChromaDB 集合前缀；若留空则从运行时上下文自动读取"] = "",
    db_params: Annotated[dict, "数据库连接参数；若留空则从运行时上下文自动读取"] = None,
    allow_llm_to_see_data: Annotated[bool, "是否允许 LLM 查看数据样例以提升 SQL 质量"] = True,
) -> dict:
    """根据自然语言问题生成 SQL 查询语句（不执行）。

    【重要】务必一次性查询所有需要的指标，不要分多次查询！
    例如：用户问"最近30天销售额"，你应该同时查询：最近30天、9月整月、历史总额等所有可能相关的指标。

    使用场景：用户提出数据查询需求时，先生成 SQL 查看是否正确。
    优先从运行时上下文读取数据源配置，无需用户每次手动传入。

    Args:
        user_question: 用户的自然语言问题，务必明确说明所有需要查询的指标（例如：'查询最近30天销售额、9月整月销售额、历史总额'）
        runtime: 运行时上下文（自动注入，无需手动传入）
        collection_prefix: ChromaDB 集合前缀；若留空则从运行时上下文自动读取
        db_params: 数据库连接参数；若留空则从运行时上下文自动读取
        allow_llm_to_see_data: 是否允许 LLM 查看数据样例以提升 SQL 质量

    Returns:
        包含 sql、ddl 的字典。
    """
    # 优先使用显式传入的参数，否则从 runtime context 读取
    ctx: AgentContext = runtime.context if runtime and runtime.context else AgentContext()
    effective_prefix = collection_prefix or ctx.datasource.collection_prefix
    effective_db_params = db_params or ctx.datasource.db_params

    if not effective_prefix or not effective_db_params:
        return {
            "error": "未找到数据源配置。请在请求中传入 datasource 参数，或在 .env 中设置默认数据源。",
            "sql": "", "ddl": [],
        }

    try:
        vn = _get_vanna(effective_prefix, effective_db_params)

        # 只生成 SQL，不执行
        sql = await run_in_threadpool(vn.generate_sql, question=user_question, allow_llm_to_see_data=allow_llm_to_see_data)
        try:
            ddl = await run_in_threadpool(vn.get_related_ddl, user_question)
        except Exception:
            ddl = []

        return {"sql": sql or "", "ddl": ddl}
    except Exception as e:
        return {"error": str(e), "sql": "", "ddl": []}


@tool(parse_docstring=True)
async def execute_sql(
    sql: Annotated[str, "要执行的 SQL 语句"],
    runtime: ToolRuntime[AgentContext],
    collection_prefix: Annotated[str, "ChromaDB 集合前缀；若留空则从运行时上下文自动读取"] = "",
    db_params: Annotated[dict, "数据库连接参数；若留空则从运行时上下文自动读取"] = None,
) -> dict:
    """执行给定的 SQL 查询语句，返回结构化结果。

    使用场景：generate_sql 生成 SQL 并确认无误后，调用此工具执行。
    优先从运行时上下文读取数据源配置，无需用户每次手动传入。

    Args:
        sql: 要执行的 SQL 语句
        runtime: 运行时上下文（自动注入，无需手动传入）
        collection_prefix: ChromaDB 集合前缀；若留空则从运行时上下文自动读取
        db_params: 数据库连接参数；若留空则从运行时上下文自动读取

    Returns:
        包含 rows、columns、data、sample_data 的字典。
    """
    # 优先使用显式传入的参数，否则从 runtime context 读取
    ctx: AgentContext = runtime.context if runtime and runtime.context else AgentContext()
    effective_prefix = collection_prefix or ctx.datasource.collection_prefix
    effective_db_params = db_params or ctx.datasource.db_params

    if not effective_prefix or not effective_db_params:
        return {
            "error": "未找到数据源配置。请在请求中传入 datasource 参数，或在 .env 中设置默认数据源。",
            "rows": 0, "columns": [], "data": "[]", "sample_data": "[]",
        }

    if not sql or not sql.strip():
        return {"error": "SQL 语句为空", "rows": 0, "columns": [], "data": "[]", "sample_data": "[]"}

    try:
        vn = _get_vanna(effective_prefix, effective_db_params)

        # 执行给定的 SQL
        df = await run_in_threadpool(vn.run_sql, sql=sql)

        if df is not None and not df.empty:
            df = df.where(pd.notnull(df), None)
            return {
                "rows": len(df),
                "columns": list(df.columns),
                "data": df.to_json(orient="records", force_ascii=False),
                "sample_data": df.sample(n=min(20, len(df))).to_json(orient="records", force_ascii=False),
            }
        else:
            return {"rows": 0, "columns": [], "data": "[]", "sample_data": "[]"}
    except Exception as e:
        return {"error": str(e), "rows": 0, "columns": [], "data": "[]", "sample_data": "[]"}


@tool(parse_docstring=True)
async def generate_compute_code(
    metrics: Annotated[str, "描述需要计算的指标或处理需求（例如：'计算各分类的销售额占比'、'按月份聚合订单量'）"],
    columns: Annotated[list, "数据列名列表"],
    sample_data: Annotated[list, "最多20行的样例数据（list of dict）"],
) -> dict:
    """根据所需计算指标和数据，生成 Python 计算代码（不执行）。

    使用场景：execute_sql 完成后，需要对数据进行进一步处理（聚合、占比、环比等）时调用。
    Agent 自主判断是否需要调用此工具。

    Args:
        metrics: 描述需要计算的指标或处理需求（例如：'计算各分类的销售额占比'、'按月份聚合订单量'）
        columns: 数据列名列表
        sample_data: 最多20行的样例数据（list of dict）

    Returns:
        包含 compute_code 的字典。
    """
    prompt = ChatPromptTemplate.from_template(Code_Decision_Prompt)
    chain = prompt | _llm
    resp = await chain.ainvoke({"metrics": metrics, "sample_data": sample_data, "columns": columns})
    decision = _safe_json_loads(resp.content.strip())

    compute_code = decision.get("compute_code", "")

    return {"compute_code": compute_code}


@tool(parse_docstring=True)
async def run_compute(
    compute_code: Annotated[str, "要执行的 Python 计算代码（仅操作 df 的部分）"],
    data: Annotated[str, "完整数据的 JSON 字符串"],
) -> dict:
    """在沙箱中执行 Python 计算代码，返回结果。

    使用场景：decide_compute 生成计算代码并确认无误后，调用此工具执行。

    Args:
        compute_code: 要执行的 Python 计算代码（仅操作 df 的部分）
        data: 完整数据的 JSON 字符串

    Returns:
        包含 code_result 的字典。
    """
    code_result = ""

    if compute_code:
        dict_data = json.loads(data) if isinstance(data, str) else data
        run_code = f"import numpy as np\nimport pandas as pd\ndf = pd.DataFrame({dict_data})\n{compute_code}"
        # 使用同步版本 + run_in_threadpool 避免 Windows asyncio subprocess 问题
        result = await run_in_threadpool(_sync_sandbox.execute, run_code)
        code_result = result.stdout if result.status == "success" else ""

    return {"code_result": code_result}


@tool(parse_docstring=True)
async def generate_charts(
    user_question: Annotated[str, "用户的自然语言问题"],
    data: Annotated[str, "数据的 JSON 字符串（优先使用 run_compute 的 code_result）"],
) -> dict:
    """根据数据和问题，决定是否生成图表并返回 ECharts 配置列表。

    使用场景：数据查询/计算完成后，判断是否适合可视化并生成图表配置。

    Args:
        user_question: 用户的自然语言问题
        data: 数据的 JSON 字符串（优先使用 run_compute 的 code_result）

    Returns:
        包含 need_charts（bool）和 charts（ECharts option 列表）的字典。
    """
    try:
        df = pd.read_json(data) if isinstance(data, str) else pd.DataFrame(data)
        if df.empty:
            return {"need_charts": False, "charts": []}

        prompt = ChatPromptTemplate.from_template(Charts_Decision_Prompt)
        chain = prompt | _llm
        resp = await chain.ainvoke({
            "input": user_question,
            "rows": len(df),
            "columns": list(df.columns),
            "sample_data": df.sample(n=min(20, len(df))).to_dict(orient="records"),
        })

        decision = _safe_json_loads(resp.content.strip())
        need_chart = decision.get("need_chart", False)
        chart_instructions = decision.get("charts", [])

        echarts_options = []
        if need_chart:
            for chart in chart_instructions:
                try:
                    option = await run_in_threadpool(generate_echarts_option, df, **chart)
                    echarts_options.append(option)
                except Exception:
                    pass

        return {"need_charts": need_chart, "charts": echarts_options}
    except Exception as e:
        return {"need_charts": False, "charts": [], "error": str(e)}


@tool(parse_docstring=True)
async def generate_analysis_report(
    user_question: Annotated[str, "用户的自然语言问题"],
    data: Annotated[str, "最终数据的 JSON 字符串（优先使用计算结果）"],
    sql: Annotated[str, "执行的 SQL 语句"],
    ddl: Annotated[list, "相关表结构（DDL 列表）"],
    user_history: Annotated[list, "近期对话历史，用于理解上下文"] = None,
) -> str:
    """生成专业的商业洞察分析报告（Markdown 格式）。

    使用场景：数据查询完成后，为用户提供深度解读、趋势分析和行动建议。

    Args:
        user_question: 用户的自然语言问题
        data: 最终数据的 JSON 字符串（优先使用计算结果）
        sql: 执行的 SQL 语句
        ddl: 相关表结构（DDL 列表）
        user_history: 近期对话历史，用于理解上下文

    Returns:
        Markdown 格式的分析报告文本。
    """
    prompt = ChatPromptTemplate.from_template(Generate_Report_Prompt)
    chain = prompt | _llm
    resp = await chain.ainvoke({
        "input": user_question,
        "data": data,
        "sql": sql,
        "ddl": ddl,
        "user_history": user_history or [],
        "now": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    return resp.content.strip()


# ─── 数据源管理工具 ────────────────────────────────────────────────────────────


@tool(parse_docstring=True)
async def list_available_datasources(runtime: ToolRuntime[AgentContext]) -> list[dict]:
    """列出当前用户已创建的数据源连接。

    使用场景：用户询问"有哪些数据库"、"能查哪些数据"，或未明确指定数据源时。
    数据从数据库 DBConnection 表中查询（与前端 /connections/list 接口一致）。

    Args:
        runtime: 运行时上下文（自动注入，用于获取 user_id）

    Returns:
        数据源列表，每项含 id、name、db_type、db_description、collection_prefix 等字段。
    """
    ctx: AgentContext = runtime.context if runtime and runtime.context else AgentContext()
    user_id = ctx.user_id

    # 1. 如果 runtime context 中已携带数据源，优先返回
    if ctx.datasource.collection_prefix and ctx.datasource.db_params:
        return [{
            "id": -1,
            "name": "请求指定数据源",
            "collection_prefix": ctx.datasource.collection_prefix,
            "db_type": ctx.datasource.db_params.get("db_type", "unknown"),
            "host": ctx.datasource.db_params.get("host", ""),
            "database": ctx.datasource.db_params.get("database", ""),
        }]

    # 2. 从 DBConnection 表查询该用户的所有数据源
    try:
        from sqlalchemy import select
        from config.database import async_session
        from config.models import DBConnection

        async with async_session() as db:
            result = await db.execute(
                select(DBConnection)
                .where(DBConnection.user_id == str(user_id))
                .order_by(DBConnection.created_at.desc())
            )
            rows = result.scalars().all()
            if rows:
                return [conn.get_safe_info() for conn in rows]
    except Exception as e:
        # 数据库不可用时，回退到空列表
        pass

    return [{"message": f"用户 {user_id} 尚未创建数据源连接，请先在前端添加数据源。"}]


# ─── 记忆辅助工具 ──────────────────────────────────────────────────────────────


@tool(parse_docstring=True)
async def save_user_preference(
    preference_key: Annotated[str, "偏好的类别，如 'chart_type'、'report_style'、'language'"],
    preference_value: Annotated[str, "偏好的具体内容"],
    runtime: ToolRuntime[AgentContext],
) -> str:
    """将用户明确表达的偏好保存到记忆文件，在后续对话中自动应用。

    使用场景：用户说"记住我喜欢折线图"、"以后报告用英文"、"不要显示SQL"等。
    调用此工具后，Agent 会通过内置的 edit_file 工具更新 /memories/AGENTS.md。

    Args:
        preference_key: 偏好的类别，如 'chart_type'、'report_style'、'language'
        preference_value: 偏好的具体内容
        runtime: 运行时上下文（自动注入，用于获取 user_id）

    Returns:
        确认消息，告知 Agent 下一步需要更新记忆文件。
    """
    ctx: AgentContext = runtime.context if runtime and runtime.context else AgentContext()
    user_id = ctx.user_id

    instruction = (
        f"请使用 edit_file 工具，将以下用户偏好写入 /memories/AGENTS.md 文件的 "
        f"<!-- USER_PREFERENCES_START --> 和 <!-- USER_PREFERENCES_END --> 之间：\n"
        f"- {preference_key}（用户 {user_id}）：{preference_value}\n"
        f"如果该 key 已存在，更新其值；不要删除其他偏好。"
    )
    return instruction



# ─── 内部工具函数 ──────────────────────────────────────────────────────────────


def _safe_json_loads(text: str) -> dict:
    """从 LLM 输出中安全提取 JSON，支持 markdown 代码块。"""
    if not isinstance(text, str):
        return {}
    raw = text.strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    for pattern in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```"]:
        match = re.search(pattern, raw, flags=re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(fix_json_string(match.group(1).strip()))
            except Exception:
                pass
    try:
        return json.loads(fix_json_string(raw))
    except Exception:
        return {}


# 导出工具列表
DATA_ANALYSIS_TOOLS = [
    # 核心工具
    generate_sql,
    execute_sql,
    generate_compute_code,
    run_compute,
    # 其他工具
    generate_charts,
    generate_analysis_report,
    list_available_datasources,
    save_user_preference,
]
