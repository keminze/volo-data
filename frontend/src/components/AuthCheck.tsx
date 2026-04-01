"use client";

import { useEffect } from "react";
import { useAuthStore } from "@/store/authStore";

export default function AuthCheck({ children }: { children: React.ReactNode }) {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    // 初始化检查认证状态
    checkAuth();
  }, [checkAuth]);

  return <>{children}</>;
}