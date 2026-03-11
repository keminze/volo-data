"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  MessageSquare,
  ChevronDown,
  ChevronRight,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react";
import { deleteChat, updateChatName } from "@/lib/api/chat";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { useChatStore } from "@/store/chatStore";
import { getOrCreateUUID } from "@/lib/utils";
import { usePathname } from "next/navigation";
export default function SidebarGroup({
  title,
  collapsed,
  expanded,
  onToggle,
}: {
  title: string;
  collapsed?: boolean;
  expanded?: boolean;
  onToggle?: () => void;
}) {
  const [open, setOpen] = useState(expanded ?? true);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const router = useRouter();
  const pathname = usePathname();
  const activeChatId = Number(pathname.split("/").pop());

  // ✅ 使用全局聊天列表
  const { chats, refreshChats, removeChat } = useChatStore();

  // 🔄 拉取聊天列表（仅在展开时）
  useEffect(() => {
    refreshChats();
  }, [refreshChats]);

  // 🧩 点击空白关闭菜单
  useEffect(() => {
    const handler = (ev: MouseEvent) => {
      if (editingId !== null || menuOpenId == null) return;
      const target = ev.target as HTMLElement;
      let el: HTMLElement | null = target;
      let inside = false;
      while (el) {
        const attr = el.getAttribute?.("data-menu-id");
        if (attr && Number(attr) === menuOpenId) {
          inside = true;
          break;
        }
        el = el.parentElement;
      }
      if (!inside) setMenuOpenId(null);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpenId, editingId]);

  // ✅ 点击外部时保存重命名
  useEffect(() => {
    if (editingId === null) return;
    const handleClickOutside = async (e: MouseEvent) => {
      if (!inputRef.current) return;
      if (!inputRef.current.contains(e.target as Node)) {
        await handleRenameConfirm(editingId);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [editingId, editValue]);

  const handleToggle = () => {
    setOpen(!open);
    onToggle?.();
  };

  // 🧩 点击聊天项
  const handleChatClick = (id: number, connection_id: number) => {
    // console.log("点击聊天，id:", id, "connection_id:", connection_id);
    router.push(`/chat/${id}?connection_id=${connection_id}`);
  };

  // ✏️ 开始重命名
  const handleRenameStart = (chatId: number, currentName: string) => {
    setEditingId(chatId);
    setEditValue(currentName);
  };

  // ✅ 确认重命名
  const handleRenameConfirm = async (chatId: number) => {
    if (!editValue.trim()) {
      setEditingId(null);
      return;
    }
    try {
      await updateChatName(chatId, { user_id: getOrCreateUUID(), name: editValue.trim() });
      await refreshChats();
    } catch (err) {
      console.error("重命名失败:", err);
      alert("重命名失败，请稍后再试");
    } finally {
      setEditingId(null);
      setMenuOpenId(null);
    }
  };

  // 🗑️ 删除聊天
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      await deleteChat(deleteTarget,getOrCreateUUID());
      removeChat(deleteTarget); // ✅ 更新全局状态
      setDeleteTarget(null);
      setMenuOpenId(null);
    } catch (err) {
      console.error("删除失败:", err);
      alert("删除失败，请稍后再试");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, chatId: number) => {
    if (e.key === "Enter") handleRenameConfirm(chatId);
    else if (e.key === "Escape") setEditingId(null);
  };

  return (
    <>
      <div className="border-t border-gray-300 mt-2">
        <button
          onClick={handleToggle}
          className="w-full flex items-center justify-between px-3 py-2 text-gray-700 hover:bg-gray-200 active:bg-gray-300 transition rounded-md"
        >
          {!collapsed && (
            <>
              <span>{title}</span>
              <span>{open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</span>
            </>
          )}
        </button>

        {open && !collapsed && (
          <div className="mt-1 ml-2 flex flex-col space-y-1">
            {chats.map((chat) => (
              <div
                key={chat.id}
                data-menu-id={chat.id}
                className={`relative group flex items-center justify-between text-sm p-2 rounded-md transition cursor-pointer
                  ${activeChatId === chat.id
                    ? "bg-gray-200 font-medium"
                    : "text-gray-700 hover:bg-gray-200"
                  }
                `}
              >
                {editingId === chat.id ? (
                  <div className="flex items-center gap-1 flex-1">
                    <input
                      ref={inputRef}
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, chat.id)}
                      className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm text-gray-800 focus:ring-2 focus:ring-blue-400 outline-none"
                      autoFocus
                    />
                  </div>
                ) : (
                  <>
                    <button
                      onClick={() => handleChatClick(chat.id, chat.connection_id)}
                      className="flex items-center text-left flex-1 min-w-0" // ✅ 关键：限制宽度以启用省略
                    >
                      <MessageSquare size={16} className="mr-2 text-gray-600 flex-shrink-0" />
                      <span className="truncate overflow-hidden text-ellipsis whitespace-nowrap text-gray-800">
                        {chat.name}
                      </span>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenId(menuOpenId === chat.id ? null : chat.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-gray-300 transition"
                    >
                      <MoreHorizontal size={16} className="text-gray-600" />
                    </button>
                    {menuOpenId === chat.id && (
                      <div className="absolute right-6 top-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg z-20 w-36">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRenameStart(chat.id, chat.name);
                          }}
                          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full"
                        >
                          <Pencil size={14} />
                          重命名
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteTarget(chat.id);
                          }}
                          className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 w-full"
                        >
                          <Trash2 size={14} />
                          删除
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        title="删除聊天"
        message="确定要删除该聊天吗？此操作不可恢复。"
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
        confirmText="删除"
      />
    </>
  );
}
