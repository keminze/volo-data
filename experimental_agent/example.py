"""
experimental_agent 使用示例 (v2)

演示以下核心功能：
1. 普通多轮对话（session_id 保持状态）
2. 人机交互（HITL）流程
3. 用户偏好记忆（跨会话持久）
4. 流式输出 + 技能触发观察
5. Runtime Context 传递
"""

import asyncio

from langchain_core.utils.uuid import uuid7
from langgraph.types import Command

from experimental_agent.agent import create_analyst_agent
from experimental_agent.context import AgentContext, DatasourceConfig


def make_ctx(user_id: str = "demo-user") -> AgentContext:
    """创建示例 AgentContext。实际使用时从请求参数构建。"""
    return AgentContext(
        user_id=user_id,
        # datasource 留空时，Agent 会调用 list_available_datasources 工具
        datasource=DatasourceConfig(),
        language="zh",
    )


async def demo_basic_chat():
    """示例 1：多轮对话（同一 session_id）。"""
    print("\n" + "=" * 60)
    print("示例 1：多轮对话 + 长期记忆")
    print("=" * 60)

    agent = create_analyst_agent()
    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id}}
    ctx = make_ctx()
    skill_files = getattr(agent, "_skill_files", {})

    # 第一轮
    r1 = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "你好，你能帮我做什么？"}], "files": skill_files},
        config=config, context=ctx, version="v2",
    )
    msgs = r1.get("messages", []) if isinstance(r1, dict) else r1.value.get("messages", [])
    print("Round 1:", next(
        (m.content for m in reversed(msgs) if hasattr(m, "content") and m.content and m.__class__.__name__ == "AIMessage"),
        ""
    ))

    # 第二轮（同一 session，Agent 记得上下文；并触发记忆写入）
    r2 = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "记住：我以后都希望用简洁的表格展示数据，不要冗长报告"}], "files": skill_files},
        config=config, context=ctx, version="v2",
    )
    msgs2 = r2.get("messages", []) if isinstance(r2, dict) else r2.value.get("messages", [])
    print("Round 2:", next(
        (m.content for m in reversed(msgs2) if hasattr(m, "content") and m.content and m.__class__.__name__ == "AIMessage"),
        ""
    ))


async def demo_hitl():
    """示例 2：人机交互（HITL）— 执行 SQL 前暂停确认。"""
    print("\n" + "=" * 60)
    print("示例 2：人机交互（HITL）")
    print("=" * 60)

    agent = create_analyst_agent(enable_hitl=True)
    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id}}
    ctx = AgentContext(
        user_id="hitl-demo",
        datasource=DatasourceConfig(
            collection_prefix="demo_prefix",
            db_params={
                "db_type": "mysql", "host": "localhost", "port": 3306,
                "username": "root", "password": "xxx", "database": "demo_db",
            },
        ),
    )
    skill_files = getattr(agent, "_skill_files", {})

    print("发起查询请求...")
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "查询最近7天的订单总量"}], "files": skill_files},
        config=config, context=ctx, version="v2",
    )

    if hasattr(result, "interrupts") and result.interrupts:
        interrupt_value = result.interrupts[0].value
        action_requests = interrupt_value.get("action_requests", [])
        review_configs = interrupt_value.get("review_configs", [])

        print("\n⏸ 检测到 HITL 中断！以下工具调用需要您确认：")
        for i, action in enumerate(action_requests):
            cfg = next((c for c in review_configs if c["action_name"] == action["name"]), {})
            print(f"  [{i}] 工具: {action['name']}")
            print(f"      参数: {action['args']}")
            print(f"      可用决策: {cfg.get('allowed_decisions', ['approve'])}")

        # 模拟用户批准
        print("\n✅ 用户选择：批准执行")
        decisions = [{"type": "approve"} for _ in action_requests]

        result2 = await agent.ainvoke(
            Command(resume={"decisions": decisions}),
            config=config, version="v2",
        )
        msgs = result2.value.get("messages", [])
        final = next(
            (m.content for m in reversed(msgs) if hasattr(m, "content") and m.content and m.__class__.__name__ == "AIMessage"),
            ""
        )
        print("执行完成:", final[:300] + "..." if len(final) > 300 else final)
    else:
        print("未触发 HITL（HITL 仅在有真实数据源且 enable_hitl=True 时触发）")


async def demo_streaming():
    """示例 3：流式输出，观察工具调用过程。"""
    print("\n" + "=" * 60)
    print("示例 3：流式输出（实时观察推理过程）")
    print("=" * 60)

    agent = create_analyst_agent()
    skill_files = getattr(agent, "_skill_files", {})
    config = {"configurable": {"thread_id": str(uuid7())}}
    ctx = make_ctx()

    print("Agent：", end="", flush=True)
    async for event in agent.astream_events(
        {"messages": [{"role": "user", "content": "介绍一下你的数据分析能力和可用工具"}], "files": skill_files},
        config=config, context=ctx, version="v2",
    ):
        kind = event.get("event")
        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and chunk.content:
                print(chunk.content, end="", flush=True)
        elif kind == "on_tool_start":
            print(f"\n  🔧 调用工具: {event.get('name')}", flush=True)
        elif kind == "on_tool_end":
            print(f"  ✓ 完成工具: {event.get('name')}", flush=True)
    print()


async def demo_skills_trigger():
    """示例 4：观察不同问题触发不同 Skill。"""
    print("\n" + "=" * 60)
    print("示例 4：Skill 库触发演示")
    print("=" * 60)

    agent = create_analyst_agent()
    skill_files = getattr(agent, "_skill_files", {})
    ctx = make_ctx()

    # 问题 → 预期触发的 Skill
    questions = [
        ("写一份关于销售下滑原因的分析报告框架", "report-writer"),
        ("帮我优化这个慢查询", "sql-optimizer"),
        ("把这份数据画成折线图", "chart-expert"),
    ]
    for q, expected_skill in questions:
        print(f"\n问题：{q}")
        print(f"预期触发 Skill：{expected_skill}")
        config = {"configurable": {"thread_id": str(uuid7())}}
        r = await agent.ainvoke(
            {"messages": [{"role": "user", "content": q}], "files": skill_files},
            config=config, context=ctx, version="v2",
        )
        msgs = r.get("messages", []) if isinstance(r, dict) else r.value.get("messages", [])
        answer = next(
            (m.content for m in reversed(msgs) if hasattr(m, "content") and m.content and m.__class__.__name__ == "AIMessage"),
            ""
        )
        print("回复预览：", answer[:200] + "..." if len(answer) > 200 else answer)


async def main():
    print("=" * 60)
    print("VoloData Deep Agent v2 — 功能演示")
    print("（涉及数据库操作的部分需要配置 .env）")
    print("=" * 60)

    await demo_basic_chat()
    await demo_streaming()
    await demo_skills_trigger()
    # HITL 需要真实数据库连接，默认注释
    # await demo_hitl()

    print("\n✅ 所有演示完成！")


if __name__ == "__main__":
    asyncio.run(main())
