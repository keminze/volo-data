"use client";

import AgentChatMessage from "./AgentChatMessage";
import ChatInput from "./ChatInput";
import { useState, useEffect, useRef } from "react";
import type { Message, ToolCallRecord } from "@/components/Chat/types";
import { DataSource } from "../DataSource/types";
import { agentStreamChat, listChatMessages } from "@/lib/api/chat";
import { message } from "antd";

interface AgentChatContainerProps {
  chatId: number;
  messages: Message[];
  connection: DataSource | null;
}

interface PendingToolCall {
  name: string;
  args?: Record<string, any>;
  result?: string;
}

export default function AgentChatContainer({ chatId, messages, connection }: AgentChatContainerProps) {
  const [localMessages, setLocalMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const assistantMsgIdRef = useRef<number | null>(null);
  const streamActiveRef = useRef<boolean>(false);
  const pendingToolsRef = useRef<PendingToolCall[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // 同步父消息
  useEffect(() => {
    setLocalMessages(messages);
  }, [messages]);

  // 监听用户滚动状态
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
      setAutoScroll(isAtBottom);
    };

    container.addEventListener("scroll", handleScroll);
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // 自动滚动
  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [localMessages, autoScroll]);

  const pushMessage = (msg: Message) => {
    setLocalMessages((prev) => [...prev, msg]);
  };

  const updateMessageContent = (id: number, updater: (old: string) => string) => {
    setLocalMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, content: updater(m.content || "") } : m))
    );
  };

  const updateMessageMeta = (id: number, patch: Partial<Message>) => {
    setLocalMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...patch } : m))
    );
  };

  // 🚀 Agent 流式发送
  const handleSend = async (text: string) => {
    if (!text || !text.trim()) return;

    // 1️⃣ 插入用户消息
    const userMsg: Message = {
      id: 0 - Date.now(),
      conversation_id: chatId,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    pushMessage(userMsg);

    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }

    // 2️⃣ 插入 AI 占位消息
    const assistantId = 0 - Date.now() + Math.floor(Math.random() * 1000);
    assistantMsgIdRef.current = assistantId;
    pushMessage({
      id: assistantId,
      conversation_id: chatId,
      role: "ai",
      content: "",
      created_at: new Date().toISOString(),
    });

    // 3️⃣ 启动 Agent 流
    setIsStreaming(true);
    streamActiveRef.current = true;
    pendingToolsRef.current = [];

    try {
      await agentStreamChat(
        {
          conversation_id: chatId,
          input: text,
          language: "zh",
        },
        {
          onToken: (tokenText) => {
            if (!streamActiveRef.current) return;
            const id = assistantMsgIdRef.current;
            if (!id) return;
            updateMessageContent(id, (old) => old + tokenText);
          },
          onToolStart: (data) => {
            if (!streamActiveRef.current) return;
            pendingToolsRef.current.push({
              name: data.tool || "unknown",
              args: data.args,
            });
          },
          onDone: () => {
            // 将收集到的工具调用写入消息
            const id = assistantMsgIdRef.current;
            if (id && pendingToolsRef.current.length > 0) {
              const toolCalls: ToolCallRecord[] = pendingToolsRef.current.map((tc, idx) => ({
                id: idx,
                tool_name: tc.name,
                tool_args: tc.args,
                tool_result: tc.result,
              }));
              updateMessageMeta(id, { tool_calls: toolCalls });
            }

            streamActiveRef.current = false;
            assistantMsgIdRef.current = null;
            setIsStreaming(false);
          },
          onError: (err) => {
            const id = assistantMsgIdRef.current;
            if (id) {
              updateMessageContent(id, () => "⚠️ 生成失败，请稍后重试。");
            }
            streamActiveRef.current = false;
            assistantMsgIdRef.current = null;
            setIsStreaming(false);
            message.error("返回报错，请重试");
            console.error(err);
          },
        }
      );
    } catch (e) {
      message.error("生成失败，请稍后重试。");
      streamActiveRef.current = false;
      assistantMsgIdRef.current = null;
      setIsStreaming(false);
      console.error(e);
    }

    // 刷新消息列表（从后端获取完整数据，含持久化的 tool_calls）
    const newMessages = await listChatMessages(chatId);
    setLocalMessages(newMessages.messages);
  };

  return (
    <div className="flex flex-col h-screen bg-white text-gray-900">
      {/* 聊天内容区域 */}
      <div ref={containerRef} className="flex-1 overflow-y-auto px-0 py-6">
        {localMessages.length === 0 ? (
          <div className="text-center text-gray-400 mt-10">
            <p className="text-lg mb-2">Agent 模式</p>
            <p className="text-sm">输入问题，Agent 将自动调用工具完成分析</p>
          </div>
        ) : (
          localMessages.map((msg) => (
            <div key={msg.id} className="max-w-4xl mx-auto w-full px-6 py-6">
              <AgentChatMessage msgdata={msg} isStreaming={isStreaming} />
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* 输入框区域 */}
      <ChatInput onSend={handleSend} connection={connection} />
    </div>
  );
}
