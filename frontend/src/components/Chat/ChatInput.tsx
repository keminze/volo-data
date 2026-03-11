"use client";
import { useState } from "react";
import { Send, Database, FileText } from "lucide-react";
import { SiMysql, SiSqlite, SiPostgresql, SiMongodb } from "react-icons/si";

export default function ChatInput({ onSend, connection }: any) {
  const [input, setInput] = useState("");

  /** ✅ 提交逻辑 */
  const handleSubmit = (e:any) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input.trim());
    setInput("");
  };

  /** ✅ 键盘事件处理（Enter 发送 / Shift+Enter 换行） */
  const handleKeyDown = (e:any) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); // 阻止默认换行
      handleSubmit(e);
    }
  };

  /** ✅ 根据 db_type 返回对应图标 */
  const getDbIcon = (dbType:string) => {
    switch ((dbType || "").toLowerCase()) {
      case "mysql":
        return <SiMysql className="text-blue-500" size={14} />;
      case "sqlite":
        return <SiSqlite className="text-purple-500" size={14} />;
      case "postgres":
      case "postgresql":
        return <SiPostgresql className="text-sky-600" size={14} />;
      case "mongodb":
        return <SiMongodb className="text-green-500" size={14} />;
      case "excel":
      case "csv":
        return <FileText className="text-green-600" size={14} />;
      default:
        return <Database className="text-gray-400" size={14} />;
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col items-center justify-center px-6 mb-4"
    >
      <div className="relative w-full max-w-3xl">
        {/* ✅ 多行输入框（支持换行） */}
        <textarea
          rows={3}
          placeholder="请输入你的问题...(Shift+Enter换行，Enter发送)"
          className="w-full h-24 pl-6 pr-10 pt-10 rounded-xl border border-gray-300 bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all text-sm resize-none"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />

        {/* ✅ 内嵌连接信息（左上角） */}
        {connection && (
          <div className="absolute left-4 top-2 flex items-center gap-1 text-[11px] text-gray-600 bg-gray-50 px-2 py-0.5 rounded-md shadow-sm">
            {getDbIcon(connection.db_type)}
            <span className="font-medium">{connection.name || "未命名连接"}</span>
            <span className="text-gray-400">({connection.db_type || "unknown"})</span>
          </div>
        )}

        {/* ✅ 右侧发送按钮 */}
        <button
          type="submit"
          className="absolute right-2 bottom-3 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md flex items-center gap-1 text-sm transition-all"
          title="发送"
        >
          <Send size={18} />
        </button>
      </div>
    </form>
  );
}
