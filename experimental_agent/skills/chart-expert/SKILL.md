---
name: chart-expert
description: 当用户明确要求"画图"、"可视化"、"图表"、"柱状图"、"折线图"、"饼图"等，或者已有数据需要专门做可视化时使用。专注于生成高质量 ECharts 图表配置。
license: MIT
metadata:
  author: volo-data
  version: "1.0"
---

# chart-expert：专业图表生成技能

## 概述

本技能专注于将数据转换为最适合的 ECharts 图表配置，包括图表类型选择和参数优化。

## 图表类型选择指南

| 场景 | 推荐图表 | 关键条件 |
|------|---------|---------|
| 时间序列趋势 | `line` | 有时间列 + 数值列 |
| 分类对比 | `bar` | 有分类列 + 数值列，类别 ≤ 20 |
| 占比/构成 | `pie` | 单个维度 + 数值，类别 ≤ 10 |
| 多维对比 | `bar`（分组/堆叠）| 有 category_col |
| 相关性分析 | `scatter` | 两个连续数值列 |
| 多指标叠加 | `line`（多系列）| 多个 y_col |

## 调用 generate_charts 的参数要求

```json
{
  "user_question": "用户原始问题",
  "data": "JSON 字符串格式的数据"
}
```

## 输出格式

将 `charts` 数组中每个 ECharts option 以 JSON 代码块输出：

```
以下是为您生成的图表配置（可直接渲染）：

```json
{ ...ECharts option... }
```
```

## 不生成图表的场景

- 数据少于 2 行
- 只有文本列，无数值列
- 用户明确说"只要数字"或"不需要图"
