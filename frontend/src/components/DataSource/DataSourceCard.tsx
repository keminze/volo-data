"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Database, FileText, Info, MessageCircle, Trash2, Loader2 } from "lucide-react";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { deleteConnection } from "@/lib/api/connections";
import { createChat } from "@/lib/api/chat";
import { useChatStore } from "@/store/chatStore"; // ✅ 引入 Zustand store
import type { DataSource } from "./types";
import { SiMysql, SiPostgresql, SiSqlite } from "react-icons/si";
import "@ant-design/v5-patch-for-react-19";
import { message } from "antd";
import { DataSourceDetailDialog } from './DataSourceDetailDialog';
import { updateConnectionInfo } from "@/lib/api/connections";
import { getOrCreateUUID } from "@/lib/utils";
export function DataSourceCard({ dataSource, isExample }: { dataSource: DataSource, isExample:boolean }) {
  const router = useRouter();
  const [showDelete, setShowDelete] = useState(false);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showDetail, setShowDetail] = useState(false);

  const addChat = useChatStore((s) => s.addChat); // ✅ 获取 addChat 函数

  /** ✅ 数据源类型图标 */
  const getIcon = (type?: string) => {
    const t = (type || "").toLowerCase();
    if (t.includes("mysql")) return <SiMysql className="h-6 w-6 text-blue-500" />;
    if (t.includes("postgres")) return <SiPostgresql className="h-6 w-6 text-indigo-500" />;
    if (t.includes("sqlite")) return <SiSqlite className="h-6 w-6 text-emerald-500" />;
    if (t.includes("csv") || t.includes("excel")) return <FileText className="h-6 w-6 text-green-500" />;
    return <Database className="h-6 w-6 text-gray-400" />;
  };

  /** ✅ 删除数据源 */
  const handleDelete = async () => {
    if (isExample){
      message.warning("示例数据源不能删除");
      return;
    }
    try {
      setLoading(true);
      await deleteConnection(Number(dataSource.id),getOrCreateUUID());
      setShowDelete(false);
      window.dispatchEvent(new CustomEvent("datasource:refresh"));
    } catch (err) {
      console.error("删除失败：", err);
      message.error("删除失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  /** ✅ 快速新建聊天（使用全局 store） */
  const handleQuickCreateChat = async () => {
    if (creating) return;
    try {
      setCreating(true);

      const res = await createChat({
        name: `未命名聊天`,
        user_id: getOrCreateUUID(), // ⚠️ 这里可替换为当前登录用户 ID
        connection_id: Number(dataSource.id),
      });

      // ✅ 获取后端返回的新聊天信息
      const newChat = {
        id: res?.conversation_id,
        name: "未命名聊天",
        connection_id: Number(dataSource.id),
      };

      // ✅ 更新全局状态（让 SidebarGroup 自动刷新）
      addChat(newChat);

      // ✅ 跳转到新聊天页面
      if (newChat.id) {
        router.push(`/chat/${newChat.id}?connection_id=${dataSource.id}`);
        message.success("聊天创建成功");
      } else {
        message.warning("创建成功，但未返回会话ID");
      }
    } catch (err) {
      console.error("新建聊天失败：", err);
      message.error("新建聊天失败，请稍后重试");
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      <motion.div
        whileHover={{ scale: 1.02 }}
        className="relative bg-gray-50 border border-gray-200 rounded-2xl px-4 pt-6 pb-6 shadow-sm hover:shadow-md transition-all duration-300 overflow-hidden"
      >
        <div className="flex items-center mb-3">
          {getIcon(dataSource.db_type)}
          <div className="ml-3 overflow-hidden">
            <h3 className="font-semibold text-gray-800 truncate">{dataSource.name}</h3>
            <p className="text-sm text-gray-500 truncate">{dataSource.db_type}</p>
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-2 pt-4">{dataSource.created_at}</p>

        {/* ✅ Hover 按钮层 */}
        <motion.div
          initial={{ opacity: 0 }}
          whileHover={{ opacity: 1 }}
          className="absolute inset-0 bg-black/40 flex items-center justify-center gap-4 rounded-2xl transition-all duration-300"
        >
          {/* {!isExample?( */}
            <button
            className="p-2 bg-white rounded-full hover:bg-gray-200 shadow"
            title="查看详情"
            onClick={() => setShowDetail(true)}
          >
            <Info className="h-4 w-4 text-yellow-700" />
          </button>
          {/* ) : null} */}
          
          <button
            onClick={handleQuickCreateChat}
            disabled={loading || creating}
            className={`p-2 bg-white rounded-full shadow transition-all ${
              creating ? "opacity-70 cursor-not-allowed" : "hover:bg-gray-200"
            }`}
            title="快速新建聊天"
          >
            {creating ? (
              <Loader2 className="h-4 w-4 text-green-700 animate-spin" />
            ) : (
              <MessageCircle className="h-4 w-4 text-green-700" />
            )}
          </button>

          {!isExample ? (<button
            className="p-2 bg-white rounded-full hover:bg-gray-200 shadow"
            title="删除数据源"
            onClick={() => setShowDelete(true)}
            disabled={loading || creating}
          >
            <Trash2 className="h-4 w-4 text-red-700" />
          </button>): null}

        </motion.div>
      </motion.div>

      {/* ✅ 删除确认弹窗 */}
      <ConfirmDialog
        open={showDelete}
        title="删除数据源"
        message={`确定要删除「${dataSource.name}」吗？此操作不可恢复。`}
        confirmText="删除"
        onConfirm={handleDelete}
        onCancel={() => setShowDelete(false)}
      />

      <DataSourceDetailDialog
        open={showDetail}
        onOpenChange={setShowDetail}
        dataSource={dataSource}
        onSave={!isExample ? async (updated) => {
          await updateConnectionInfo(
            dataSource.id,
            {
              user_id: getOrCreateUUID(), // ⚠️ 根据实际情况替换
              new_name: updated.name,
              new_description: updated.db_description,
            }
          );
          window.dispatchEvent(new CustomEvent("datasource:refresh"));
        } : undefined}
      />

      {/* ✅ 全屏加载遮罩层 */}
      {creating && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/50 backdrop-blur-sm text-white">
          <Loader2 className="h-10 w-10 animate-spin mb-3" />
          <p className="text-sm opacity-90">正在创建聊天，请稍候...</p>
        </div>
      )}
    </>
  );
}
