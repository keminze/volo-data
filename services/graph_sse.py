# app/main.py
import datetime
import json
from decimal import Decimal
from typing import TypedDict

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from langgraph.graph import StateGraph

from config.logging_config import logger
from redis_client import redis_client

# from langgraph.config import get_stream_writer
from services.tools import (
    chart_decision_tool,
    code_decision_tool,
    gen_sql_and_execution_tool,
    generate_chart_tool,
    run_code_tool,
    safe_json_loads,
    stream_generate_report_tool,
)

load_dotenv()


# ========= LangGraph =========
class State(TypedDict):
    task_id: str
    input: str
    collection_prefix: str
    db_params: dict
    sql: str
    data: dict
    need_charts: bool
    charts: dict
    report: str
    allow_llm_to_see_data: bool
    user_history: list
    skip_charts: bool
    skip_report: bool
    ddl: list
    needs_compute: bool
    compute_code: str
    code_result: str


def safe_convert(value):
    """安全转换为JSON可序列化类型"""
    if isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, (pd.Timestamp, datetime.datetime)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    elif pd.isna(value):  # 处理 NaN/None
        return None
    return value


def build_graph():
    stream_workflow = StateGraph(State)

    # 节点定义
    async def sql_node(state: State):
        try:
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
                # 替换 NaN，MySQL JSON 不支持 NaN
                df = df.replace({np.nan: None})

                data_dict = {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "sample_data": (
                        df.sample(n=min(20, len(df))).to_json(orient="records")
                        if len(df) > 0
                        else []
                    ),
                    "data": df.to_json(
                        orient="records"
                    ),  # ✅ 注意：一定要转成 list of dict 才能 JSON 序列化
                }
            else:
                data_dict = {"rows": 0, "columns": [], "data": "", "sample_data": ""}

            await redis_client.rpush(
                f"task_stream:{state['task_id']}",
                json.dumps(
                    {
                        "event": "node_done",
                        "data": {
                            "sql": sql,
                            "data": json.loads(data_dict["data"]),
                            "node": "sql_exec",
                            "timestamp": datetime.datetime.now().isoformat(),
                        },
                    },
                    default=safe_convert,
                ),
            )
            logger.info(f"sql_node done:{data_dict}")
            return {"sql": sql, "data": data_dict, "ddl": ddl}

        except Exception as e:
            logger.error(f"Error in sql_node: {str(e)}", exc_info=True)
            await redis_client.rpush(
                f"task_stream:{state['task_id']}",
                json.dumps(
                    {
                        "event": "error",
                        "data": {
                            "error": str(e),
                            "node": "sql_exec",
                            "timestamp": datetime.datetime.now().isoformat(),
                        },
                    },
                    default=safe_convert,
                ),
            )
            raise Exception("SQL execution failed :", str(e)) from e

    async def code_decision_node(state):
        try:
            sample_data = state["data"]["sample_data"]
            columns = state["data"]["columns"]
            input_question = state["input"]
            data = state["data"]["data"]

            dict_sample_data = (
                json.loads(sample_data) if isinstance(sample_data, str) else sample_data
            )
            res = await code_decision_tool(input_question, dict_sample_data, columns)

            code_decision = safe_json_loads(res)
            needs_compute = code_decision.get("needs_compute", False)
            compute_code = code_decision.get("compute_code", "")
            res_code = ""
            if needs_compute:
                logger.info(f"run_code_tool: {compute_code}")
                dict_data = json.loads(data) if isinstance(data, str) else data
                res_code = await run_code_tool(compute_code, dict_data)
                logger.info(f"run_code_tool done: {res_code}")
                try:
                    safe_json_loads(res_code)
                except Exception as e:
                    logger.error(f"Error in load JSON: {str(e)}", exc_info=True)
                    raise Exception("Code execution failed :", str(e)) from e

            await redis_client.rpush(
                f"task_stream:{state['task_id']}",
                json.dumps(
                    {
                        "event": "node_done",
                        "data": {
                            "needs_compute": needs_compute,
                            "compute_code": compute_code,
                            "code_result": res_code,
                            "node": "code_decision",
                            "timestamp": datetime.datetime.now().isoformat(),
                        },
                    },
                    default=safe_convert,
                ),
            )

            logger.info(f"code_decision_node: {res}")

            return {
                "needs_compute": needs_compute,
                "compute_code": compute_code,
                "code_result": res_code,
            }

        except Exception as e:
            logger.error(f"Error in code_decision_node: {str(e)}", exc_info=True)
            await redis_client.rpush(
                f"task_stream:{state['task_id']}",
                json.dumps(
                    {
                        "event": "error",
                        "data": {
                            "error": str(e),
                            "node": "code_decision",
                            "timestamp": datetime.datetime.now().isoformat(),
                        },
                    },
                    default=safe_convert,
                ),
            )

    async def charts_decision_node(state):
        try:
            if state["code_result"]:
                data = state["code_result"]
            else:
                data = state["data"]["data"]
            df = pd.read_json(data)
            res = await chart_decision_tool(
                state["input"],
                len(df),
                list(df.columns),
                df.sample(n=min(20, len(df))).to_dict(orient="records") if len(df) > 0 else [],
            )

            # ✅ 安全加载 JSON
            decision = safe_json_loads(res)

            need_chart = decision.get("need_chart", False)
            chart_instructions = decision.get("charts", [])
            res_charts = []

            if need_chart:
                logger.info(f"Chart will be generated: {chart_instructions}")
                res_charts = await generate_chart_tool(df, chart_instructions)

            # SSE 输出
            await redis_client.rpush(
                f"task_stream:{state['task_id']}",
                json.dumps(
                    {
                        "event": "node_done",
                        "data": {
                            "need_charts": need_chart,
                            "charts": res_charts,
                            "node": "charts_decision",
                            "timestamp": datetime.datetime.now().isoformat(),
                        },
                    },
                    default=safe_convert,
                ),
            )

            logger.info(f"charts_decision_node done: {decision}")

            return {"need_charts": need_chart, "charts": chart_instructions}

        except Exception as e:
            logger.error(f"Error in charts_decision_node: {str(e)}", exc_info=True)
            await redis_client.rpush(
                f"task_stream:{state['task_id']}",
                json.dumps(
                    {
                        "event": "error",
                        "data": {
                            "error": str(e),
                            "node": "charts_decision",
                            "timestamp": datetime.datetime.now().isoformat(),
                        },
                    },
                    default=safe_convert,
                ),
            )
            raise Exception("Chart decision failed:", str(e)) from e

    async def report_node(state):
        try:
            gen_report = await stream_generate_report_tool(
                state["input"],
                state["data"]["data"],
                state["code_result"],
                state["user_history"],
                state["sql"],
                state["ddl"],
            )
            report = ""
            async for chunk in gen_report:
                text = getattr(chunk, "content", "") or ""
                report += text
                await redis_client.rpush(
                    f"task_stream:{state['task_id']}",
                    json.dumps(
                        {
                            "event": "node_message",
                            "data": {
                                "message_chunk": text,
                                "node": "report",
                                "timestamp": datetime.datetime.now().isoformat(),
                            },
                        },
                        default=safe_convert,
                    ),
                )
            await redis_client.rpush(
                f"task_stream:{state['task_id']}",
                json.dumps(
                    {
                        "event": "node_done",
                        "data": {
                            "report": report,
                            "node": "report",
                            "timestamp": datetime.datetime.now().isoformat(),
                        },
                    },
                    default=safe_convert,
                ),
            )
            logger.info(f"report_node done:{report}")
            return {"report": report}
        except Exception as e:
            logger.error(f"Error in report_node: {str(e)}", exc_info=True)
            await redis_client.rpush(
                f"task_stream:{state['task_id']}",
                json.dumps(
                    {
                        "event": "error",
                        "data": {
                            "error": str(e),
                            "node": "report",
                            "timestamp": datetime.datetime.now().isoformat(),
                        },
                    },
                    default=safe_convert,
                ),
            )
            raise Exception("Report generation failed :", str(e)) from e

    async def merge_node(state):
        return state

    # 条件边
    def after_sql_exec(state: dict):
        skip_report = state.get("skip_report", False)
        skip_charts = state.get("skip_charts", False)

        # 1. 优先级最高：全部跳过
        if skip_report and skip_charts:
            return "merge"

        # 2. 只有一边需要执行
        if skip_charts:
            return "report"
        if skip_report:
            return "charts_decision"

        # 3. 两边都需要执行 (并行分叉)
        return ["charts_decision", "report"]

    # 添加节点
    stream_workflow.add_node("sql_exec", sql_node)
    stream_workflow.add_node("code_decision", code_decision_node)
    stream_workflow.add_node("charts_decision", charts_decision_node)
    stream_workflow.add_node("report", report_node)
    stream_workflow.add_node("merge", merge_node)

    stream_workflow.add_edge("sql_exec", "code_decision")

    # 定义边
    stream_workflow.add_conditional_edges(
        "code_decision",
        after_sql_exec,
        path_map={"report": "report", "charts_decision": "charts_decision", "merge": "merge"},
    )

    stream_workflow.add_edge("charts_decision", "merge")
    stream_workflow.add_edge("report", "merge")

    stream_workflow.set_entry_point("sql_exec")
    stream_workflow.set_finish_point("merge")

    return stream_workflow.compile()


graph = build_graph()
