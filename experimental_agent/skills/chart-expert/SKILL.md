---
name: chart-expert
description: 当用户明确要求"画图"、"可视化"、"图表"、"柱状图"、"折线图"、"饼图"等，或者已有数据需要专门做可视化时使用。专注于生成高质量 ECharts 图表配置。
license: MIT
metadata:
  author: volo-data
  version: "1.0"
---

# chart-expert：专业图表生成技能

## 图表类型选择指南

| 场景 | 推荐图表 | 关键条件 |
|------|---------|---------|
| 时间序列趋势 | `line` | 有时间列 + 数值列 |
| 分类对比 | `bar` | 有分类列 + 数值列，类别 ≤ 20 |
| 占比/构成 | `pie` | 单个维度 + 数值，类别 ≤ 10 |
| 多维对比 | `bar`（分组/堆叠）| 有 category_col |
| 相关性分析 | `scatter` | 两个连续数值列 |
| 多指标叠加 | `line`（多系列）| 多个 y_col |
