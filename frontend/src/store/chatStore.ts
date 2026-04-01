// src/store/chatStore.ts
import { create } from "zustand";
import { listChat } from "@/lib/api/chat";

interface Chat {
  id: number;
  name: string;
  connection_id: number;
}

interface ChatStore {
  chats: Chat[];
  setChats: (chats: Chat[]) => void;
  addChat: (chat: Chat) => void;
  removeChat: (chatId: number) => void;
  refreshChats: () => Promise<void>;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  chats: [],
  setChats: (chats) => set({ chats }),
  addChat: (chat) => set((state) => ({ chats: [chat, ...state.chats] })),
  removeChat: (chatId) =>
    set((state) => ({ chats: state.chats.filter((c) => c.id !== chatId) })),
  refreshChats: async () => {
    try {
      const res = await listChat();
      set({ chats: res || [] });
    } catch (err) {
      console.error("加载聊天列表失败:", err);
    }
  },
}));