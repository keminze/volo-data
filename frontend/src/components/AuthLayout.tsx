"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import Sidebar from "@/components/Sidebar/Sidebar";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, checkAuth, token } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const [initialized, setInitialized] = useState(false);

  // 只在挂载后检查一次认证状态
  useEffect(() => {
    const init = async () => {
      if (token && !isAuthenticated) {
        await checkAuth();
      }
      setInitialized(true);
    };
    init();
  }, []); // 空依赖，只执行一次

  // 处理路由跳转
  useEffect(() => {
    if (!initialized || isLoading) return;

    const isAuthPage = pathname === "/auth";

    // 未登录且不在登录页，跳转到登录
    if (!isAuthenticated && !isAuthPage) {
      router.replace("/auth");
    }
    // 已登录且在登录页，跳转到主页
    else if (isAuthenticated && isAuthPage) {
      router.replace("/");
    }
  }, [initialized, isLoading, isAuthenticated, pathname, router]);

  // 加载中
  if (!initialized || isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-white">
        <div className="text-slate-500">Loading...</div>
      </div>
    );
  }

  // 登录页全屏显示
  if (pathname === "/auth") {
    return <div className="w-full h-screen">{children}</div>;
  }

  // 已登录显示侧边栏
  return (
    <>
      <Sidebar />
      <main className="flex-1 bg-gray-50">{children}</main>
    </>
  );
}