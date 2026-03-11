# import asyncio
import datetime
import json
import os
import re

import pandas as pd
from dotenv import load_dotenv
from fastapi.concurrency import run_in_threadpool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config.logging_config import logger
from langchain_sandbox import PyodideSandbox
from services.db import CollectionSuffix, chromadb_client, connect_to_database
from services.prompt import Charts_Decision_Prompt, Code_Decision_Prompt, Generate_Report_Prompt
from services.vanna_service import Vanna

sandbox = PyodideSandbox(
    # Allow Pyodide to install python packages that
    # might be required.
    allow_net=True,
    allow_read=True,
    allow_write=True,
)

load_dotenv()

llm = ChatOpenAI(
    model_name=os.getenv("OPENAI_MODEL"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_BASE_URL"),
)

stream_llm = ChatOpenAI(
    model_name=os.getenv("OPENAI_MODEL"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base=os.getenv("OPENAI_BASE_URL"),
    streaming=True,
)

# async def gen_query_tool(user_query: str):
#     prompt = ChatPromptTemplate.from_template(Charts_Decision_Prompt)
#     pass


async def gen_sql_and_execution_tool(
    collection_prefix, query, db_params, allow_llm_to_see_data: bool
) -> tuple[str, "pd.DataFrame"]:
    try:
        vn = Vanna(
            {
                "client": chromadb_client,
                "documentation_collection_name": f"{collection_prefix}_{CollectionSuffix.DOCUMENTATION.value}",
                "ddl_collection_name": f"{collection_prefix}_{CollectionSuffix.DDL.value}",
                "sql_collection_name": f"{collection_prefix}_{CollectionSuffix.SQL.value}",
            }
        )
        connect_to_database(vn, db_params=db_params)

        sql, df, _ = await run_in_threadpool(
            vn.ask, question=query, visualize=False, allow_llm_to_see_data=allow_llm_to_see_data
        )
        try:
            ddl = await run_in_threadpool(vn.get_related_ddl, query)
        except Exception as e:
            logger.error(f"Error in get_related_ddl: {str(e)}", exc_info=True)
            ddl = []
        return sql if sql else "", df, ddl
    except Exception as e:
        logger.error(f"Error in gen_sql_and_execution_tool: {str(e)}", exc_info=True)
        return "", pd.DataFrame(), []


async def chart_decision_tool(input: str, rows: int, columns: list, sample_data):
    """判断是否需要画图，并生成echarts图表基本信息"""
    prompt = ChatPromptTemplate.from_template(Charts_Decision_Prompt)
    chain = prompt | llm  # LCEL 风格

    resp = await chain.ainvoke(
        {"input": input, "rows": rows, "columns": columns, "sample_data": sample_data}
    )
    # decision = json.loads(resp.content.strip())
    # print("decision:",resp.content.strip())
    return resp.content.strip()


def generate_echarts_option(
    df,
    chart_type: str,
    x_col: str,
    y_col,
    category_col: str = None,
    stacked: bool = False,
    title: str = "",
):
    if isinstance(df, list):
        df = pd.DataFrame(df)

    y_cols = [y_col] if isinstance(y_col, str) else y_col

    if category_col:
        df[category_col] = df[category_col].astype(str).str.strip()

    # ✅ 先处理 pie，不执行依赖 x_col 的 groupby
    if chart_type == "pie":
        if category_col:
            group_data = (
                df.groupby(category_col)[y_cols[0]]
                .sum()
                .reset_index()
                .sort_values(by=y_cols[0], ascending=False)
            )

            # 超过 20 个类别时，做“其他”合并
            if len(group_data) > 20:
                top20 = group_data.iloc[:20].copy()
                others = group_data.iloc[20:]
                other_value = others[y_cols[0]].sum()
                other_row = {category_col: "其他", y_cols[0]: other_value}
                final_group_data = pd.concat([top20, pd.DataFrame([other_row])], ignore_index=True)
            else:
                final_group_data = group_data

            data = [
                {"name": row[category_col], "value": row[y_cols[0]]}
                for _, row in final_group_data.iterrows()
            ]

        else:
            # ⭐ 当没有 category_col 时，对 x_col 做相同逻辑 ⭐
            group_data = (
                df.groupby(x_col)[y_cols[0]]
                .sum()
                .reset_index()
                .sort_values(by=y_cols[0], ascending=False)
            )

            if len(group_data) > 20:
                top20 = group_data.iloc[:20].copy()
                others = group_data.iloc[20:]
                other_value = others[y_cols[0]].sum()
                other_row = {x_col: "其他", y_cols[0]: other_value}
                final_group_data = pd.concat([top20, pd.DataFrame([other_row])], ignore_index=True)
            else:
                final_group_data = group_data

            data = [
                {"name": row[x_col], "value": row[y_cols[0]]}
                for _, row in final_group_data.iterrows()
            ]

        return {
            "title": {"text": title},
            "tooltip": {"trigger": "item"},
            "legend": {"orient": "vertical", "left": "left"},
            "series": [{"name": title or y_cols[0], "type": "pie", "radius": "50%", "data": data}],
        }

    # ✅ pie 已 return，不会走到这里
    # 下面是 bar / line / area 等图表
    if category_col and x_col:
        df = df.groupby([category_col, x_col])[y_cols].sum().reset_index()
    elif x_col:
        df = df.groupby(x_col)[y_cols].sum().reset_index()
    else:
        raise ValueError("x_col cannot be None for non-pie charts")

    x_data = sorted(df[x_col].unique().tolist())

    series = []
    legend_names = []

    if category_col:
        for cat in sorted(df[category_col].unique()):
            sub_df = df[df[category_col] == cat].set_index(x_col)
            for y in y_cols:
                name = f"{cat}-{y}" if len(y_cols) > 1 else str(cat)
                legend_names.append(name)
                y_data = sub_df[y].reindex(x_data).fillna(0).tolist()
                s = {"name": name, "type": chart_type, "data": y_data}
                if stacked and chart_type in ["bar", "line"]:
                    s["stack"] = "total"
                series.append(s)
    else:
        sub_df = df.set_index(x_col)
        for y in y_cols:
            legend_names.append(y)
            y_data = sub_df[y].reindex(x_data).fillna(0).tolist()
            s = {"name": y, "type": chart_type, "data": y_data}
            if stacked and chart_type in ["bar", "line"]:
                s["stack"] = "total"
            series.append(s)

    return {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": legend_names},
        "xAxis": {"type": "category", "data": x_data},
        "yAxis": {"type": "value"},
        "series": series,
    }


async def generate_chart_tool(df, charts):
    """生成图表（返回 ECharts JSON）"""

    echarts_options = []
    for chart in charts:
        try:
            # print("chart",chart)
            echarts_option = await run_in_threadpool(generate_echarts_option, df, **chart)
            # print("echart_option",echart_option)
            echarts_options.append(echarts_option)
        except Exception as e:
            logger.error(f"Error in generate_echarts_option:{str(e)}", exc_info=True)
    if len(echarts_options) == 0:
        logger.error("No echarts option generated, but need charts.")
    # print("echart_options",echarts_options)
    return echarts_options


async def code_decision_tool(input: str, sample_data: list, columns: list):
    prompt = ChatPromptTemplate.from_template(Code_Decision_Prompt)
    chain = prompt | llm  # LCEL 风格
    resp = await chain.ainvoke({"input": input, "sample_data": sample_data, "columns": columns})
    return resp.content.strip()


async def run_code_tool(code: str, data: list) -> str:
    run_code = f"import numpy as np\nimport pandas as pd\ndf = pd.DataFrame({data})\n{code}"
    # print("run_code:",run_code)
    """在沙箱中执行 Python 代码的异步函数"""
    # return await sandbox.execute(run_code)
    result = await sandbox.execute(run_code)
    if result.status == "success":
        return result.stdout
    else:
        raise Exception(f"Sandbox code execution error: {result.stderr}")


async def stream_generate_report_tool(
    input: str, data, code_result, user_history: list, sql, ddl: list
):
    """根据数据生成报告"""
    if code_result:
        data = code_result
    prompt = ChatPromptTemplate.from_template(Generate_Report_Prompt)

    chain = prompt | stream_llm  # LCEL 风格
    return chain.astream(
        {
            "input": input,
            "data": data,
            "user_history": user_history,
            "sql": sql,
            "ddl": ddl,
            "now": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


async def generate_report_tool(input: str, data: dict, user_history: list, sql, ddl: list):
    """根据数据生成报告"""
    # print("generate_report_tool start",datetime.datetime.now())
    prompt = ChatPromptTemplate.from_template(Generate_Report_Prompt)
    chain = prompt | llm  # LCEL 风格
    resp = await chain.ainvoke(
        {"input": input, "data": data, "user_history": user_history, "sql": sql, "ddl": ddl}
    )
    # print("generate_report_tool end",datetime.datetime.now())
    return resp.content.strip()


def safe_json_loads(text: str):
    """
    安全加载 JSON：
    支持：
    - 普通 JSON 字符串
    - markdown 中的 JSON 代码块 ```json ... ```
    - markdown 中未标注语言的 ``` ... ```
    - 自动修复常见 JSON 错误（换行、单引号、尾逗号）
    解析失败返回 {}
    """
    if not isinstance(text, str):
        return {}

    raw = text.strip()

    # --------------------------------
    # 1) 尝试直接解析
    # --------------------------------
    try:
        return json.loads(raw)
    except Exception:
        pass

    # --------------------------------
    # 2) 提取 markdown ```json code block```
    # --------------------------------

    # ```json  ...  ```
    pattern_json_block = r"```json\s*(.*?)\s*```"
    match = re.search(pattern_json_block, raw, flags=re.DOTALL | re.IGNORECASE)
    if match:
        code = match.group(1).strip()
        fixed = fix_json_string(code)
        try:
            return json.loads(fixed)
        except Exception:
            pass

    # ```  ...  ```
    pattern_code_block = r"```\s*(.*?)\s*```"
    match = re.search(pattern_code_block, raw, flags=re.DOTALL)
    if match:
        code = match.group(1).strip()
        fixed = fix_json_string(code)
        try:
            return json.loads(fixed)
        except Exception:
            pass

    # --------------------------------
    # 3) 尝试修复 JSON
    # --------------------------------
    fixed = fix_json_string(raw)
    try:
        return json.loads(fixed)
    except Exception as e:
        logger.error(f"safe_json_loads failed: {e}, raw text: {raw}")
        return {}


def fix_json_string(s: str):
    """
    修复常见 JSON 格式问题：
    - 去除换行符
    - 单引号转双引号
    - 去除尾逗号
    """
    s = s.replace("\r", "").replace("\n", "")

    # 单引号 → 双引号（注意避免 `'text'` 出错）
    if "'" in s and '"' not in s:
        s = s.replace("'", '"')

    # 尾逗号处理：  {"a":1,} → {"a":1}
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)

    return s
