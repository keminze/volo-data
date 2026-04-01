"use client";

import Image from "next/image";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import { Database, Plus, LogOut, Languages } from "lucide-react";
import { cn } from "@/lib/utils";
import SidebarItem from "./SidebarItem";
import SidebarGroup from "./SidebarGroup";
import { NewChatDialog } from "@/components/Chat/NewChatDialog";
import { useAuthStore } from "@/store/authStore";

export default function Sidebar() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [showHistory, setShowHistory] = useState(true);
  const [showNewChat, setShowNewChat] = useState(false);
  const { isAuthenticated, logout } = useAuthStore();

  const handleNavigation = (path: string) => {
    router.push(path);
  };

  const toggleLanguage = () => {
    const newLang = i18n.language === "zh-CN" ? "en-US" : "zh-CN";
    i18n.changeLanguage(newLang);
  };

  const handleLogout = () => {
    logout();
    router.push("/auth");
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
          {/* 主页按钮 */}
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
            label={t("sidebar.home")}
            collapsed={collapsed}
            onClick={() => handleNavigation("/")}
          />

          <SidebarItem
            icon={<Database size={18} />}
            label={t("sidebar.dataSources")}
            collapsed={collapsed}
            onClick={() => handleNavigation("/data_sources")}
          />

          <SidebarItem
            icon={<Plus size={18} />}
            label={t("sidebar.newChat")}
            collapsed={collapsed}
            onClick={() => setShowNewChat(true)}
          />
        </div>

        {/* 历史聊天分组 */}
        <SidebarGroup
          title={t("sidebar.history")}
          collapsed={collapsed}
          expanded={showHistory}
          onToggle={() => setShowHistory(!showHistory)}
        />
      </div>

      {/* 底部功能区 - 垂直排列 */}
      <div className="p-2 border-t border-gray-300 flex flex-col gap-2">
        {isAuthenticated && (
          <button
            onClick={handleLogout}
            className={cn(
              "flex items-center gap-2 w-full p-2 rounded-lg bg-red-500 hover:bg-red-600 text-white transition-all duration-200",
              collapsed && "justify-center"
            )}
            title={t("auth.logout")}
          >
            <LogOut size={16} />
            {!collapsed && <span className="text-sm">{t("auth.logout")}</span>}
          </button>
        )}

        {/* 语言切换 */}
        <button
          onClick={toggleLanguage}
          className={cn(
            "flex items-center gap-2 w-full p-2 rounded-lg bg-gray-200 hover:bg-gray-300 transition-all duration-200",
            collapsed && "justify-center"
          )}
          title={t("language.switch")}
        >
          <Languages size={16} className="text-gray-700" />
          {!collapsed && <span className="text-sm text-gray-700">{t("language.switch")}</span>}
        </button>

        {/* 折叠按钮 */}
        <button
          onClick={() => setCollapsed((prev) => !prev)}
          className={cn(
            "flex items-center gap-2 w-full p-2 rounded-lg bg-gray-200 hover:bg-gray-300 transition-all duration-200",
            collapsed && "justify-center"
          )}
        >
          <span className="text-xl font-medium text-gray-700">
            {collapsed ? "›" : "‹"}
          </span>
          {!collapsed && <span className="text-sm text-gray-700">{collapsed ? "展开" : "收起"}</span>}
        </button>
      </div>

      <NewChatDialog open={showNewChat} onOpenChange={setShowNewChat} />
    </div>
  );
}
