"use client";

import Image from "next/image"; // ✅ 新增
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Database, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import SidebarItem from "./SidebarItem";
import SidebarGroup from "./SidebarGroup";
import { NewChatDialog } from "@/components/Chat/NewChatDialog";

export default function Sidebar() {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [showHistory, setShowHistory] = useState(true);
  const [showNewChat, setShowNewChat] = useState(false);

  const handleNavigation = (path: string) => {
    router.push(path); // ✅ 不要加 `/` 两次
  };

  return (
    <div
      className={cn(
        "flex flex-col justify-between bg-gray-100 text-gray-900 h-screen border border-gray-300 shadow-sm transition-all duration-300 rounded-r-2xl overflow-hidden",
        collapsed ? "w-16" : "w-56"
      )}
    >
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* 顶部按钮组 */}
        <div className="p-2">

          {/* ✅ 新增：主页按钮 */}
          <SidebarItem
            icon={
              <Image
                src="/favicon.ico"
                alt="Home"
                width={18}
                height={18}
                className="rounded-sm"
              />
            }
            label="主页"
            collapsed={collapsed}
            onClick={() => handleNavigation("/")}
          />

          <SidebarItem
            icon={<Database size={18} />}
            label="数据源"
            collapsed={collapsed}
            onClick={() => handleNavigation("/data_sources")}
          />

          <SidebarItem
            icon={<Plus size={18} />}
            label="新建聊天"
            collapsed={collapsed}
            onClick={() => setShowNewChat(true)}
          />
        </div>

        {/* 历史聊天分组 */}
        <SidebarGroup
          title="历史聊天"
          collapsed={collapsed}
          expanded={showHistory}
          onToggle={() => setShowHistory(!showHistory)}
        />
      </div>

      {/* 折叠按钮 */}
      <div className="p-2 border-t border-gray-300 flex justify-center">
        <button
          onClick={() => setCollapsed((prev) => !prev)}
          className="flex items-center justify-center px-6 py-1 rounded-full bg-gray-200 hover:bg-gray-300 transition-all duration-200"
        >
          <span className="text-2xl font-medium text-gray-700">
            {collapsed ? "›" : "‹"}
          </span>
        </button>
      </div>

      <NewChatDialog open={showNewChat} onOpenChange={setShowNewChat} />
    </div>
  );
}
