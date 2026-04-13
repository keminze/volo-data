---
name: sql-optimizer
description: 当用户询问"为什么SQL慢"、"优化查询"、"SQL报错怎么修"、"解释这段SQL"、"写一个复杂查询"时使用。专注于SQL诊断、优化和解释。
license: MIT
metadata:
  author: volo-data
  version: "1.0"
---

# sql-optimizer：SQL 专家技能

## 概述

本技能提供 SQL 诊断、优化建议和查询解释，帮助用户理解和改进数据库查询。

## 技能范围

### 1. SQL 错误诊断
当 `execute_sql_query` 返回 `error` 字段时：
- 解析错误类型（语法错误、表不存在、权限不足、超时等）
- 给出具体的修复建议
- 如果是表名/列名问题，参考 DDL 提示正确名称

### 2. SQL 性能优化建议
当用户询问慢查询时，检查：
- 是否使用了 `SELECT *`（建议指定列）
- JOIN 条件是否有索引
- WHERE 条件列是否有索引
- 是否存在 N+1 查询
- 子查询是否可改写为 JOIN

### 3. 查询解释
将复杂 SQL 翻译为自然语言，解释每个子句的作用。

### 4. 查询辅助生成
对于复杂业务需求，先理解业务逻辑，再调用 `execute_sql_query`：
- 窗口函数（RANK、ROW_NUMBER、LAG/LEAD）
- CTE（公用表表达式）
- 条件聚合（CASE WHEN SUM）

## 重要约束
- 不直接拼接 SQL 字符串给用户执行，始终通过 `execute_sql_query` 工具执行
- 不猜测表结构，使用 DDL 作为权威来源
- 遇到权限问题，建议用户联系数据库管理员
