"use client";

import { cn } from "@/lib/utils";

export default function SidebarItem({
  icon,
  label,
  active,
  collapsed,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  collapsed?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center w-full rounded-md text-gray-700 transition-all duration-200",
        "hover:bg-gray-200 active:bg-gray-300", // ✅ hover效果
        active ? "bg-gray-300 font-semibold" : "bg-transparent",
        collapsed ? "justify-center p-2" : "justify-start px-3 py-2"
      )}
    >
      <span className="flex-shrink-0">{icon}</span>
      {!collapsed && <span className="ml-2 truncate">{label}</span>}
    </button>
  );
}
