"use client";

import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import { useState, useEffect, useRef } from "react";
import type { Message } from "@/components/Chat/types";
import { DataSource } from "../DataSource/types";
import { listenStreamTask, submitStreamTask } from "@/lib/api/chat";
import { getOrCreateUUID } from "@/lib/utils";
import { message } from "antd"
import { listChatMessages } from "@/lib/api/chat";

interface ChatContainerProps {
  chatId: number;
  messages: Message[];
  connection: DataSource | null;
}

export default function ChatContainer({ chatId, messages, connection }: ChatContainerProps) {
  const [localMessages, setLocalMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isGeneratingSQL, setIsGeneratingSQL] = useState(false);
  const [isGeneratingCharts, setIsGeneratingCharts] = useState(false);
  const assistantMsgIdRef = useRef<number | null>(null);
  const streamActiveRef = useRef<boolean>(false);
  const bottomRef = useRef<HTMLDivElement>(null);
    // 自动滚动到底部（智能模式）
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
      // 判断是否接近底部（距离底部 100px 内视为在底部）
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
      setAutoScroll(isAtBottom);
    };

    container.addEventListener("scroll", handleScroll);
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // 当新消息到来时，仅在用户未脱离底部时滚动
  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [localMessages, autoScroll]);

  // 添加消息
  const pushMessage = (msg: Message) => {
    setLocalMessages((prev) => [...prev, msg]);
  };

  // 更新消息内容
  const updateMessageContent = (id: number, updater: (old: string) => string) => {
    setLocalMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, content: updater(m.content || "") } : m))
    );
  };

  // 更新消息的附加字段（如 sql、charts 等）
  const updateMessageMeta = (id: number, patch: Partial<Message>) => {
    setLocalMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...patch } : m))
    );
  };

  // 🧩 处理 node_done：更新已有的 assistant 消息
  const handleNodeDone = (data: any) => {
    const nodeType = data?.node || "unknown";
    const id = assistantMsgIdRef.current;
    if (!id) return;

    switch (nodeType) {
      // case "report":
      //   updateMessageContent(id, (old) => {
      //     const newText =
      //       data?.report ||
      //       "(无报告内容)";
      //     return (old + "\n\n" + newText).trim();
      //   });
      //   break;

      case "sql_exec":
        updateMessageMeta(id, {
          sql: data?.sql ?? data?.executed_sql ?? "",
          sample_data: data?.data ?? null,
        });
        setIsGeneratingSQL(false);
        break;
      
      case "code_decision":
        updateMessageMeta(id, {
          compute_code: data?.compute_code ?? "",
          code_result: data?.code_result ?? "",
        });
        // console.log("code_decision:", data);
        break;
        
      case "charts_decision":
        updateMessageMeta(id, {
          charts: data?.charts ?? data?.chart_config ?? null,
        });
        setIsGeneratingCharts(false);
        break;

      default:
        console.warn("Unhandled node_done type:", nodeType, data);
        break;
    }
  };

  // 🚀 发送并开始流式接收
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
        behavior: "smooth", // 平滑滚动
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

    // 3️⃣ 启动流
    setIsStreaming(true);
    setIsGeneratingSQL(true);
    setIsGeneratingCharts(true);
    streamActiveRef.current = true;

    try {
       const submit_res = await submitStreamTask(
        {
          user_id: getOrCreateUUID(),
          conversation_id: chatId,
          input: text,
          allow_llm_to_see_data: true,
          skip_charts: false,
          skip_report: false,
        }
      );
      console.log("submitStreamTask task_id:", submit_res.task_id);

      await listenStreamTask(
        submit_res.task_id,
        {
          onNodeMessage: (data) => {
            if (!streamActiveRef.current) return;
            const chunk =
              data?.message_chunk ?? "";
            if (!chunk) return;
            const id = assistantMsgIdRef.current;
            if (!id) return;
            updateMessageContent(id, (old) => old + chunk);
          },
          onNodeDone: (data) => {
            if (!streamActiveRef.current) return;
            handleNodeDone(data);
          },
          onEnd: () => {
            // const id = assistantMsgIdRef.current;
            // if (id) {
            //   updateMessageContent(id, (old) => old.trim() || "(无返回内容)");
            // }
            streamActiveRef.current = false;
            assistantMsgIdRef.current = null;
            setIsStreaming(false);
            setIsGeneratingCharts(false);
            setIsGeneratingSQL(false);
          },
          onError: (err) => {
            const id = assistantMsgIdRef.current;
            if (id) {
              updateMessageContent(id, () => "⚠️ 生成失败，请稍后重试。");
            } else {
              pushMessage({
                id: Date.now() + 2,
                conversation_id: chatId,
                role: "ai",
                content: "⚠️ 生成失败，请稍后重试。",
                created_at: new Date().toISOString(),
              });
            }
            streamActiveRef.current = false;
            assistantMsgIdRef.current = null;
            setIsStreaming(false);
            setIsGeneratingCharts(false);
            setIsGeneratingSQL(false);
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
      setIsGeneratingCharts(false);
      setIsGeneratingSQL(false);
      console.error(e);
    }
    const new_messages = await listChatMessages(chatId)
    setLocalMessages(new_messages.messages)
  };

  return (
    <div className="flex flex-col h-screen bg-white text-gray-900">
      {/* 聊天内容区域 */}
      <div ref={containerRef} className="flex-1 overflow-y-auto px-0 py-6">
        {localMessages.length === 0 ? (
          <p className="text-center text-gray-400 mt-10">暂无聊天记录</p>
        ) : (
          localMessages.map((msg) => (
            <div key={msg.id} className="max-w-4xl mx-auto w-full px-6 py-6">
              <ChatMessage msgdata={msg} isStreaming={isStreaming} isGeneratingSQL={isGeneratingSQL} isGeneratingCharts={isGeneratingCharts} />
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
