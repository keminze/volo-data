"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { listChatMessages } from "@/lib/api/chat";
import { getConnectionInfo } from "@/lib/api/connections";
import ChatContainer from "@/components/Chat/ChatContainer";
import type { Message } from "@/components/Chat/types";
import type { DataSource } from "@/components/DataSource/types";
import { useChatStore } from "@/store/chatStore";
import { getOrCreateUUID } from "@/lib/utils";

export default function ChatPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const chatId = Number(params.id);
  const connectionId = Number(searchParams.get("connection_id"));
  const [messages, setMessages] = useState<Message[]>([]);
  const [connection, setConnection] = useState<DataSource | null>(null);

  const { chats } = useChatStore();

  // ✅ 判断 chat 是否存在
  const chatExists = chats.some((c) => c.id === chatId);

  useEffect(() => {
    if (!chatId || !chatExists) return;
    (async () => {
      try {
        const res = await listChatMessages(chatId);
        setMessages(res.messages || []);
      } catch (err) {
      }
    })();
  }, [chatId, chatExists]);

  useEffect(() => {
    if (!connectionId) return;
    getConnectionInfo(connectionId, getOrCreateUUID())
      .then((data: DataSource) => setConnection(data))
      .catch((err) => {
        setConnection(null);
      });
  }, [connectionId]);

  if (!chatExists) {
    return null;
  }

  return <ChatContainer chatId={chatId} messages={messages} connection={connection} />;
}
