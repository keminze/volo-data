"use client";
import React,{useEffect, useRef} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { base16AteliersulphurpoolLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message } from "./types";
import { CopyOutlined } from "@ant-design/icons";
import { Button, message, Tooltip } from "antd";
import MeesageCard from "./MessageCard";
import { Spin } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import { CodeOutlined } from "@ant-design/icons";

export default function ChatMessage({ msgdata, isStreaming, isGeneratingSQL, isGeneratingCharts }: { msgdata: Message, isStreaming:boolean, isGeneratingSQL:boolean, isGeneratingCharts:boolean }) {
  const isUser = msgdata.role === "user";
  const isGen = msgdata.id < 0;

  function childrenContainsPre(node: React.ReactNode): boolean {
    if (!node) return false;
    if (Array.isArray(node)) {
      return node.some(childrenContainsPre);
    }
    // 如果是 react element
    if (React.isValidElement(node)) {
      const type = (node as any).type;
      if (type === "pre") return true;
      // 递归检测其 props.children
      return childrenContainsPre((node as any).props?.children);
    }
    return false;
}

  /** 📋 复制 Markdown 内容 */
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(msgdata.content);
      message.success("内容已复制");
    } catch {
      message.error("复制失败");
    }
  };

  /** 🔁 重新生成（占位） */
  // const handleRegenerate = () => {
  //   message.info("重新生成功能待接入后端");
  // };

  return (
    <div
      className={`w-full flex mb-4 ${
        isUser ? "justify-end" : "justify-center flex-col items-center"
      }`}
    >
      {/* <div className="flex flex-col relative w-full"> */}
        {msgdata.role === "ai" && (
          <>
            <MeesageCard
              sql={msgdata.sql}
              sample_data={msgdata.sample_data}
              charts={msgdata.charts}
              isGeneratingSQL={isGen && isGeneratingSQL}
              isGeneratingCharts={isGen && isGeneratingCharts}
            />

            {/* 🌀 正在进行数据分析提示 */}
            {isGen && (isGeneratingSQL || isGeneratingCharts) && (
              <div className="flex items-center justify-center gap-2 mt-2 mb-1 text-gray-400 text-xs">
                <Spin
                  indicator={
                    <LoadingOutlined
                      style={{ fontSize: 14, color: "#9ca3af" }}
                      spin
                    />
                  }
                />
                <span>正在进行数据分析</span>
              </div>
            )}
          </>
        )}
        {/* 🧠 可折叠代码展示块（仅当 compute_code 存在） */}
        {msgdata.role === "ai" && msgdata.compute_code && (
          <details
            className="
              w-full max-w-[70%]
              group mb-3
              rounded-xl
              bg-white
              border border-gray-200
              shadow-sm
              transition-shadow
              hover:shadow-md
              open:shadow-md
            "
          >
            <summary
              className="
                cursor-pointer select-none
                flex items-center gap-2
                px-4 py-2
                text-sm text-gray-600
                hover:text-gray-800
                list-none
              "
            >
              <CodeOutlined
                className="
                  transition-transform duration-300
                  group-open:rotate-90
                "
              />
              <span>查看计算代码</span>
            </summary>

            {/* 👇 展开动画容器 */}
            <div
              className="
                overflow-hidden
                transition-all duration-300 ease-in-out
                max-h-0 opacity-0 translate-y-[-4px]
                group-open:max-h-[1000px]
                group-open:opacity-100
                group-open:translate-y-0
              "
            >
              {/* 内容区域 */}
              <div className="px-4 pb-3 pt-3 space-y-3 text-sm border-t border-gray-100">
                {/* 计算代码 */}
                <div>
                  {/* <div className="text-gray-500 mb-1">计算代码</div> */}
                  <SyntaxHighlighter
                    language="python"
                    style={base16AteliersulphurpoolLight}
                    customStyle={{
                      margin: 0,
                      padding: "12px",
                      fontSize: "12px",
                      borderRadius: "8px",
                    }}
                  >
                    {msgdata.compute_code}
                  </SyntaxHighlighter>
                </div>

                {/* 执行结果 */}
                {msgdata.code_result && (
                  <div>
                    <div className="text-gray-500 mb-1">执行结果</div>
                    <pre className="bg-gray-50 border border-gray-200 rounded-md p-2 overflow-x-auto text-xs">
                      <code>{msgdata.code_result}</code>
                    </pre>
                  </div>
                )}
              </div>
            </div>
          </details>
        )}
        <div
          className={`
            relative px-5 py-3 rounded-2xl text-[15px] leading-relaxed break-words
            ${
              isUser
                ? // ✅ 用户消息：有最大最小宽度，随屏幕变化
                  "bg-gray-100 text-black min-w-[150px] max-w-[50%]"
                : // ✅ AI消息：固定比例，保持统一宽度
                  "bg-white text-gray-900 w-[90%] sm:w-[85%] md:w-[80%] lg:w-[70%]"
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
                h2: ({ children }) => <h2 className="text-base font-semibold mt-3 mb-1">{children}</h2>,

                // 关键：对 <p> 做保护性处理，避免 p 包含 pre 导致错误
                p: ({ children }) => {
                  // 若 children 中含有 pre（代码块），直接返回 children（不包裹 p）
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
                    <table className="min-w-full border border-gray-300 text-sm">{children}</table>
                  </div>
                ),
                thead: ({ children }) => <thead className="bg-gray-100 text-gray-700">{children}</thead>,
                th: ({ children }) => (
                  <th className="border border-gray-300 px-3 py-1 font-medium text-left">{children}</th>
                ),
                td: ({ children }) => (
                  <td className="border border-gray-300 px-3 py-1 align-top">{children}</td>
                ),
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-blue-400 pl-3 italic text-gray-700 my-2">
                    {children}
                  </blockquote>
                ),

                // code：inline 用 <code>，block 用 <pre><code>
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
                    <pre
                      className="inline-flex bg-[#f7f7f8] text-gray-900 p-1 rounded-lg 
                                overflow-x-auto text-sm border border-gray-200 my-1"
                    >
                      <code className={className} {...props}>
                        {children}
                      </code>
                    </pre>
                  );
                },
              }}
            >
              {msgdata.content}
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
              {/* <Tooltip title="重新生成">
                <Button
                  size="small"
                  type="text"
                  icon={<RedoOutlined />}
                  onClick={handleRegenerate}
                />
              </Tooltip> */}
            </div>
          )}
        </div>
      {/* </div> */}
    </div>
  );
}
