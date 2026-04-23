---
name: data-analysis
description: 当用户提出数据查询、数据分析、查看报表、统计、趋势分析等需求时使用本技能。核心原则：一次查够，工具最少化。
license: MIT
metadata:
  author: volo-data
  version: "2.0"
---

# data-analysis：高效数据分析流程

## ⚠️ 最高优先级：工具最少化原则

**严禁：**
- 先查一点看看，再查另一点
- 把一个问题拆成多次 SQL 查询
- 简单单位转换（分↔元）也用 Python 工具
- SQL 工具调用超过 2 次

**必须：**
- 一次 SQL 查询所有需要的指标
- 简单计算直接在回复里做
- 调用工具前先规划完整路径

## 分析流程

### 1. 确认数据源
- 未指定数据源时，调用 `list_available_datasources`
- 从 runtime context 读取配置

### 2. 一次性 SQL 查询（关键步骤）
调用 `generate_sql`，明确告诉它：**一次性查询所有需要的指标**
- 例如："查询最近30天销售额、9月整月销售额、历史总额"
- 不要分开查！

然后调用 `execute_sql` 执行。

### 3. 二次计算（仅在必要时）
- 只有复杂计算才用 `generate_compute_code` + `run_compute`
- 简单计算直接在回复里算

### 4. 生成图表和报告
- `generate_charts` + `generate_analysis_report`

## 输出规范
1. 展示 SQL（折叠）
2. 图表（如有）
3. 分析报告
4. "如需进一步分析，请继续提问"
