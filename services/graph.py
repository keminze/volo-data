# app/main.py
import json
from typing import TypedDict

import numpy as np
from dotenv import load_dotenv
from langgraph.graph import StateGraph

from services.tools import (
    chart_decision_tool,
    gen_sql_and_execution_tool,
    generate_chart_tool,
    generate_report_tool,
)

load_dotenv()


# ========= LangGraph =========
class State(TypedDict):
    input: str
    collection_prefix: str
    db_params: dict
    sql: str
    data: dict
    chart_decision: dict
    charts: dict
    report: str
    allow_llm_to_see_data: bool
    user_history: list
    skip_charts: bool
    skip_report: bool
    ddl: list


workflow = StateGraph(State)


def build_graph():
    workflow = StateGraph(State)

    # 节点定义
    async def sql_node(state):
        collection_prefix = state.get("collection_prefix")
        if not collection_prefix:
            raise ValueError("Missing collection_prefix in state")
        db_params = state.get("db_params")
        if not db_params:
            raise ValueError("Missing db_params in state")

        sql, df, ddl = await gen_sql_and_execution_tool(
            collection_prefix, state["input"], db_params, state["allow_llm_to_see_data"]
        )

        if df is not None and not df.empty:
            # 替换掉 NaN，MySQL JSON 不支持 NaN
            df = df.replace({np.nan: None})
            data_dict = {
                "rows": len(df),
                "cloumns": list(df.columns),
                "sample_data": (
                    df.sample(n=min(20, len(df))).to_dict(orient="records") if len(df) > 0 else []
                ),
                "data": df,
            }
        else:
            data_dict = {"rows": 0, "cloumns": [], "sample_data": df, "data": df}
        return {"sql": sql, "data": data_dict, "ddl": ddl}

    async def charts_decision_node(state):
        res = await chart_decision_tool(
            state["input"],
            state["data"]["rows"],
            state["data"]["cloumns"],
            state["data"]["sample_data"],
        )
        decision = json.loads(res)
        charts = []
        if decision.get("need_chart"):
            charts = await generate_chart_tool(state["data"]["data"], decision.get("charts"))
        return {"need_charts": decision.get("need_chart"), "charts": charts}

    async def report_node(state):
        report = await generate_report_tool(
            state["input"],
            state["data"]["data"].to_dict(orient="records"),
            state["user_history"],
            state["sql"],
            state["ddl"],
        )
        # ✅只返回 report
        return {"report": report}

    async def merge_node(state):
        return state

    # 条件边
    def after_sql_exec(state: dict):
        # 跳过生成报告和图表
        if state.get("skip_report") and state.get("skip_charts"):
            return "merge"
        # 跳过生成图表
        if state.get("skip_charts"):
            return "report"
        # 跳过生成报告
        if state.get("skip_report"):
            return "charts_decision"
        # 执行所有
        else:
            return ["charts_decision", "report"]

    def after_charts_decision(state: dict):
        chart_decision = state.get("chart_decision")
        if chart_decision.get("need_chart"):
            return "charts"
        else:
            return "merge"

    # 添加节点
    workflow.add_node("sql_exec", sql_node)
    workflow.add_node("charts_decision", charts_decision_node)
    workflow.add_node("report", report_node)
    workflow.add_node("merge", merge_node)

    # 定义边
    workflow.add_conditional_edges(
        "sql_exec",
        after_sql_exec,
        path_map={"report": "report", "charts_decision": "charts_decision", "merge": "merge"},
    )

    workflow.add_edge("charts_decision", "merge")
    workflow.add_edge("report", "merge")

    workflow.set_entry_point("sql_exec")
    workflow.set_finish_point("merge")

    return workflow.compile()


graph = build_graph()
