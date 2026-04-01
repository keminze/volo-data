"use client";

import { useEffect, useState } from "react";
import { I18nextProvider } from "react-i18next";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import enUS from "antd/locale/en_US";
import i18n from "@/i18n";
import { useAuthStore } from "@/store/authStore";
import { setTokenGetter } from "@/lib/api/request";

export function Providers({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState(zhCN);
  const { checkAuth, token } = useAuthStore();

  useEffect(() => {
    const handleLanguageChange = (lng: string) => {
      setLocale(lng === "en-US" ? enUS : zhCN);
    };

    handleLanguageChange(i18n.language);

    i18n.on("languageChanged", handleLanguageChange);
    return () => {
      i18n.off("languageChanged", handleLanguageChange);
    };
  }, []);

  // 初始化认证状态
  useEffect(() => {
    // 设置 token getter
    setTokenGetter(() => useAuthStore.getState().token);

    // 检查认证状态
    checkAuth();
  }, []);

  return (
    <I18nextProvider i18n={i18n}>
      <ConfigProvider locale={locale}>
        {children}
      </ConfigProvider>
    </I18nextProvider>
  );
}