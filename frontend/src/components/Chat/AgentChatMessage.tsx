"use client";
import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { CopyOutlined } from "@ant-design/icons";
import { Button, message as antMessage, Tooltip, Spin } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import AgentToolCallCard from "./AgentToolCallCard";
import AgentChartCard from "./AgentChartCard";
import type { Message, ToolCallRecord } from "./types";

export default function AgentChatMessage({
  msgdata,
  isStreaming,
}: {
  msgdata: Message;
  isStreaming: boolean;
}) {
  const { t } = useTranslation();
  const isUser = msgdata.role === "user";
  const isGen = msgdata.id < 0;

  function childrenContainsPre(node: React.ReactNode): boolean {
    if (!node) return false;
    if (Array.isArray(node)) {
      return node.some(childrenContainsPre);
    }
    if (React.isValidElement(node)) {
      const type = (node as any).type;
      if (type === "pre") return true;
      return childrenContainsPre((node as any).props?.children);
    }
    return false;
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(msgdata.content);
      antMessage.success("内容已复制");
    } catch {
      antMessage.error("复制失败");
    }
  };

  // 预处理：转义波浪号，避免被 remarkGfm 解析为删除线
  const escapeTildes = (text: string) => text.replace(/~/g, "\\~");

  // 预处理：剥离文本中残留的工具调用 JSON（LLM 有时会把工具参数混入正文）
  const stripToolJson = (text: string): string => {
    const TOOL_KEYS = ["need_chart", "need_charts", "chart_type", "x_col", "y_col", "category_col", "stacked"];
    // 匹配 {...} 或包含换行的 {...} 块
    return text.replace(/\{[\s\S]*?\}/g, (match) => {
      // 如果 JSON 块中包含已知工具参数 key，则整块移除
      if (TOOL_KEYS.some((k) => match.includes(`"${k}"`))) {
        return "";
      }
      return match;
    }).replace(/\n{3,}/g, "\n\n"); // 清理多余空行
  };

  // 组合预处理：先剥离工具 JSON，再转义波浪号
  const preprocess = (text: string) => escapeTildes(stripToolJson(text));

  // 将 tool_calls 转为 AgentToolCallCard 需要的格式
  const toolCallEntries = (msgdata.tool_calls || []).map((tc: ToolCallRecord) => ({
    name: tc.tool_name,
    args: tc.tool_args,
    result: tc.tool_result,
  }));

  // 从 generate_charts 工具结果中提取图表配置
  let charts: any[] = [];
  const chartsCall = (msgdata.tool_calls || []).find(
    (tc: ToolCallRecord) => tc.tool_name === "generate_charts"
  );
  if (chartsCall?.tool_result) {
    try {
      const parsed = typeof chartsCall.tool_result === "string"
        ? JSON.parse(chartsCall.tool_result)
        : chartsCall.tool_result;
      if (parsed.need_charts && Array.isArray(parsed.charts) && parsed.charts.length > 0) {
        charts = parsed.charts;
      }
    } catch {}
  }

  return (
    <div
      className={`w-full flex mb-4 ${
        isUser ? "justify-end" : "justify-center flex-col items-center"
      }`}
    >
      {/* 工具调用卡片（AI 消息，有 tool_calls 时显示） */}
      {msgdata.role === "ai" && toolCallEntries.length > 0 && (
        <AgentToolCallCard toolCalls={toolCallEntries} />
      )}

      {/* 图表卡片（generate_charts 工具返回图表时显示） */}
      {msgdata.role === "ai" && charts.length > 0 && (
        <AgentChartCard charts={charts} />
      )}

      {/* 流式加载提示 */}
      {msgdata.role === "ai" && isGen && isStreaming && (
        <div className="flex items-center justify-center gap-2 mt-2 mb-1 text-gray-400 text-xs">
          <Spin
            indicator={
              <LoadingOutlined style={{ fontSize: 14, color: "#9ca3af" }} spin />
            }
          />
          <span>{t("chat.agentThinking")}</span>
        </div>
      )}

      {/* 消息内容 */}
      <div
        className={`
          relative px-5 py-3 rounded-2xl text-[15px] leading-relaxed break-words mt-3
          ${
            isUser
              ? "bg-gray-100 text-black min-w-[150px] max-w-[50%]"
              : "bg-white text-gray-900 w-[90%] sm:w-[85%] md:w-[80%] lg:w-[70%]"
          }
        `}
      >
        <div className="markdown-body w-full">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
            components={{
              h1: ({ children }) => (
                <h1 className="text-center text-lg font-bold mt-3 mb-2 border-b border-gray-300 pb-1">
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-base font-semibold mt-3 mb-1">{children}</h2>
              ),
              p: ({ children }) => {
                if (childrenContainsPre(children)) {
                  return <>{children}</>;
                }
                return <p className="my-2">{children}</p>;
              },
              ul: ({ children }) => (
                <ul className="list-disc list-inside my-2 ml-2 space-y-1">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-inside my-2 ml-2 space-y-1">{children}</ol>
              ),
              li: ({ children }) => <li className="ml-1">{children}</li>,
              table: ({ children }) => (
                <div className="overflow-x-auto my-3">
                  <table className="min-w-full border border-gray-300 text-sm">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => (
                <thead className="bg-gray-100 text-gray-700">{children}</thead>
              ),
              th: ({ children }) => (
                <th className="border border-gray-300 px-3 py-1 font-medium text-left">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="border border-gray-300 px-3 py-1 align-top">{children}</td>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-blue-400 pl-3 italic text-gray-700 my-2">
                  {children}
                </blockquote>
              ),
              code: ({ inline, className, children, ...props }: any) => {
                if (inline) {
                  return (
                    <code
                      className="bg-gray-200 text-gray-900 px-1 py-0.5 rounded text-[0.9em]"
                      {...props}
                    >
                      {children}
                    </code>
                  );
                }
                return (
                  <pre className="inline-flex bg-[#f7f7f8] text-gray-900 p-1 rounded-lg overflow-x-auto text-sm border border-gray-200 my-1">
                    <code className={className} {...props}>
                      {children}
                    </code>
                  </pre>
                );
              },
            }}
          >
            {preprocess(msgdata.content)}
          </ReactMarkdown>
        </div>

        {msgdata.role === "ai" && msgdata.content?.trim() && !isStreaming && (
          <div className="flex justify-end gap-2 mt-3">
            <Tooltip title="复制">
              <Button
                size="small"
                type="text"
                icon={<CopyOutlined />}
                onClick={handleCopy}
              />
            </Tooltip>
          </div>
        )}
      </div>
    </div>
  );
}
