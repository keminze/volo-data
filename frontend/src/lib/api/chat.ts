import { apiRequest, getToken } from "@/lib/api/request";
import { API_BASE } from "@/lib/api/request";
import type { Message } from "@/components/Chat/types";

/**
 * 🧩 聊天会话相关类型定义
 */
export interface ChatResponse {
  id: number;
  user_id: string;
  name: string;
  connection_id: number;
  description?: string;
  mode?: string;
  created_at?: string;
}

export interface CreateChatRequest {
  name: string;
  connection_id: number;
  description?: string;
  mode?: string;
}

export interface CreateChatResponse {
  message: string;
  conversation_id: number;
}

export interface MessageResponse {
  messages: Message[];
}

export interface submitStreamTaskResponse {
  task_id: string
}

/**
 * 🟢 创建新聊天
 * @param request 创建聊天的请求体
 */
export async function createChat(request: CreateChatRequest) {
  return apiRequest<CreateChatResponse>("/conversations/create", {
    method: "POST",
    body: request,
  });
}

/**
 * 🟣 获取聊天列表
 * @param mode 可选模式筛选：workflow / agent
 */
export async function listChat(mode?: string) {
  const query = mode ? `?mode=${mode}` : "";
  return apiRequest<ChatResponse[]>(`/conversations/list${query}`, {
    method: "GET",
  });
}

/**
 * 🔵 获取指定会话的消息列表
 * @param chatId 聊天会话 ID
 */
export async function listChatMessages(chatId: number) {
  return apiRequest<MessageResponse>(
    `/conversations/${chatId}/messages`,
    { method: "GET" }
  );
}

/**
 * 🟠 更新聊天名称
 * @param chatId 聊天会话 ID
 * @param name 新名称
 */
export async function updateChatName(
  chatId: number,
  name: string
) {
  return apiRequest<{ message: string }>(`/conversations/update/${chatId}`, {
    method: "PUT",
    body: { name },
  });
}

/**
 * 🔴 删除聊天
 * @param chatId 聊天会话 ID
 */
export async function deleteChat(chatId: number) {
  return apiRequest<{ message: string }>(
    `/conversations/delete/${chatId}`,
    {
      method: "DELETE",
    }
  );
}

export async function submitStreamTask(
      payload: {
        conversation_id: number;
        input: string;
        allow_llm_to_see_data: boolean;
        skip_charts: boolean;
        skip_report: boolean;
      }){
      return apiRequest<submitStreamTaskResponse>(`/generate/stream`, {
        method: "POST",
        body: payload,
    })
}

/**
 * 🟢 Agent 流式对话（SSE）
 * 直接连接 /agent/chat/stream，事件类型：token / tool_start / tool_result / interrupt / done / error
 */
export async function agentStreamChat(
  payload: {
    conversation_id: number;
    input: string;
    language?: string;
  },
  handlers: {
    onToken?: (text: string) => void;
    onToolStart?: (data: { tool: string; args: any }) => void;
    onToolResult?: (data: { tool: string; result: string }) => void;
    onInterrupt?: (data: any) => void;
    onDone?: () => void;
    onError?: (err: any) => void;
  }
) {
  try {
    const token = getToken ? getToken() : null;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    } else if (process.env.NEXT_PUBLIC_BACKEND_API_KEY) {
      headers["x-api-key"] = process.env.NEXT_PUBLIC_BACKEND_API_KEY;
    }

    const response = await fetch(`${API_BASE}/agent/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (!response.ok || !response.body) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split(/\r?\n\r?\n/);
      buffer = parts.pop() || "";

      for (const part of parts) {
        if (!part.trim()) continue;

        try {
          const eventMatch = part.match(/^event:\s*(.+)$/m);
          const dataMatch = part.match(/^data:\s*(.+)$/m);

          if (!dataMatch) continue;
          const event = eventMatch ? eventMatch[1].trim() : "message";
          const data = JSON.parse(dataMatch[1]);

          switch (event) {
            case "token":
              handlers.onToken?.(data.text || "");
              break;
            case "tool_start":
              handlers.onToolStart?.(data);
              break;
            case "tool_result":
              handlers.onToolResult?.(data);
              break;
            case "interrupt":
              handlers.onInterrupt?.(data);
              break;
            case "done":
              handlers.onDone?.();
              break;
            case "error":
              handlers.onError?.(data);
              break;
          }
        } catch (err) {
          console.warn("Agent SSE parse error:", err, part);
        }
      }
    }
  } catch (err) {
    console.error("Agent SSE stream error:", err);
    handlers.onError?.(err);
  }
}

export async function listenStreamTask(
  task_id: string,
  handlers: {
    onNodeDone?: (data: any) => void;
    onNodeMessage?: (data: any) => void;
    onEnd?: () => void;
    onError?: (err: any) => void;
  }
) {
  try {
    const token = getToken ? getToken() : null;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    } else if (process.env.NEXT_PUBLIC_BACKEND_API_KEY) {
      headers["x-api-key"] = process.env.NEXT_PUBLIC_BACKEND_API_KEY;
    }

    const response = await fetch(`${API_BASE}/generate/task_stream/${task_id}`, {
      method: "GET",
      headers,
    });

    if (!response.ok || !response.body) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    // 持续读取后端的SSE流
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // 支持 \r\n\r\n 和 \n\n 两种格式
      const parts = buffer.split(/\r?\n\r?\n/);
      buffer = parts.pop() || "";

      for (const part of parts) {
        if (!part.trim()) continue;

        try {
          const eventMatch = part.match(/^event:\s*(.+)$/m);
          const dataMatch = part.match(/^data:\s*(.+)$/m);

          if (!dataMatch) continue;
          const event = eventMatch ? eventMatch[1].trim() : "message";
          const data = JSON.parse(dataMatch[1]);

          if (event === "node_done") handlers.onNodeDone?.(data);
          else if (event === "node_message") handlers.onNodeMessage?.(data);
          else if (event === "end") handlers.onEnd?.();
          else if (event === "error") handlers.onError?.(data);
        } catch (err) {
          console.warn("SSE parse error:", err, part);
        }
      }
    }

    handlers.onEnd?.();
  } catch (err) {
    console.error("SSE stream error:", err);
    handlers.onError?.(err);
  }
}