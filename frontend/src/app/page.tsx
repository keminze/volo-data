"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

export default function Home() {
  const { t } = useTranslation();
  const fullText = t("home.welcome");
  const [displayedText, setDisplayedText] = useState("");
  const [showGuide, setShowGuide] = useState(false);

  useEffect(() => {
    let index = 0;
    const text = t("home.welcome");
    const interval = setInterval(() => {
      setDisplayedText(text.slice(0, index + 1));
      index++;
      if (index === text.length) {
        clearInterval(interval);
        setTimeout(() => setShowGuide(true), 600);
      }
    }, 120);
    return () => clearInterval(interval);
  }, [t]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-white text-black px-6">
      {/* 添加图标 */}
      <Image
        src="/favicon.ico"
        alt="logo"
        width={64}
        height={64}
        className="mb-4"
      />

      {/* 打字主标题 */}
      <h1 className="text-3xl sm:text-4xl font-bold tracking-wide h-[2.5em]">
        {displayedText}
        <span className="inline-block w-[8px] bg-black ml-1 animate-pulse" />
      </h1>

      {/* 使用指南（淡入动画） */}
      {showGuide && (
        <div className="mt-8 text-gray-600 text-sm sm:text-base leading-relaxed whitespace-pre-line text-left animate-fadeIn">
          {t("home.quickStart")}{"\n"}
          {t("home.step1")} <code className="bg-gray-100 px-1 rounded">{t("home.dataSource")}</code>
          {t("home.step1Suffix")}{"\n"}
          {t("home.step2")} <code className="bg-gray-100 px-1 rounded">{t("home.quickCreate")}</code>
          {t("home.step2Suffix")}
        </div>
      )}

      <style jsx global>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 1s ease-out;
        }
      `}</style>
    </div>
  );
}
