// src/store/chatStore.ts
import { create } from "zustand";
import { listChat } from "@/lib/api/chat";

interface Chat {
  id: number;
  name: string;
  connection_id: number;
  mode?: string; // "workflow" | "agent"
}

interface ChatStore {
  chats: Chat[];
  workflowChats: Chat[];
  agentChats: Chat[];
  setChats: (chats: Chat[]) => void;
  addChat: (chat: Chat) => void;
  removeChat: (chatId: number) => void;
  refreshChats: () => Promise<void>;
}

function splitChats(chats: Chat[]) {
  return {
    workflowChats: chats.filter((c) => (c.mode || "workflow") === "workflow"),
    agentChats: chats.filter((c) => c.mode === "agent"),
  };
}

export const useChatStore = create<ChatStore>((set, get) => ({
  chats: [],
  workflowChats: [],
  agentChats: [],
  setChats: (chats) => set({ chats, ...splitChats(chats) }),
  addChat: (chat) =>
    set((state) => {
      const chats = [chat, ...state.chats];
      return { chats, ...splitChats(chats) };
    }),
  removeChat: (chatId) =>
    set((state) => {
      const chats = state.chats.filter((c) => c.id !== chatId);
      return { chats, ...splitChats(chats) };
    }),
  refreshChats: async () => {
    try {
      const res = await listChat();
      const chats = res || [];
      set({ chats, ...splitChats(chats) });
    } catch (err) {
      console.error("加载聊天列表失败:", err);
    }
  },
}));
