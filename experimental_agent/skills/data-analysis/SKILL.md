---
name: data-analysis
description: 当用户提出数据查询、数据分析、查看报表、统计、趋势分析等需求时使用本技能。执行完整的数据分析流程：确定数据源 → 生成并执行SQL → 判断是否需要二次计算 → 生成图表 → 输出洞察报告。
license: MIT
metadata:
  author: volo-data
  version: "1.0"
---

# data-analysis：完整数据分析流程

## 概述

本技能指导 Agent 完成端到端的数据分析任务，从自然语言问题到最终的可视化报告。

## 分析流程（严格按顺序执行）

### 第一步：确认数据源
- 如果用户消息中未包含 `collection_prefix` 或 `db_params`，调用 `list_available_datasources` 列出可用数据源
- 如果只有一个数据源，直接使用；如果多个，询问用户选择哪个
- 从 runtime context 的 `datasource` 字段读取已传入的数据源配置

### 第二步：执行 SQL 查询
调用 `execute_sql_query`，传入：
- `collection_prefix`：数据源标识
- `user_question`：用户的原始问题（不要改写）
- `db_params`：数据库连接参数
- `allow_llm_to_see_data`：默认 `true`

**处理空结果**：若 `rows == 0`，直接告知用户无数据，无需后续步骤。

### 第三步：判断是否需要二次计算
调用 `decide_and_run_compute`，传入第二步返回的 `columns`、`sample_data`、`data`。
- 如果 `needs_compute == false`，跳过本步，使用原始 `data`
- 如果 `needs_compute == true`，使用 `code_result` 作为后续步骤的数据

### 第四步：生成图表（按需）
调用 `generate_charts`，传入用户问题和最终数据（`code_result` 或原始 `data`）。
- 将返回的 `charts` 数组作为 JSON 代码块输出给用户（前端直接渲染）

### 第五步：生成分析报告
调用 `generate_analysis_report`，传入：
- `user_question`、`data`（最终数据）、`sql`、`ddl`
- `user_history`：从对话历史中提取之前的问答

## 输出格式规范

1. 先展示 SQL（折叠代码块）
2. 如有图表，输出 `charts` JSON
3. 输出分析报告（Markdown）
4. 末尾附加一句"如需进一步分析，请继续提问"

## 注意事项
- 数值精度：保留 3 位小数
- 严禁自行换算单位（如分↔元）
- 如果查询报错，解释错误并建议修正方向
