"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

export default function Home() {
  const fullText = "欢迎使用 Volo Data 智能数据分析助手";
  const [displayedText, setDisplayedText] = useState("");
  const [showGuide, setShowGuide] = useState(false);

  useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      setDisplayedText(fullText.slice(0, index + 1));
      index++;
      if (index === fullText.length) {
        clearInterval(interval);
        setTimeout(() => setShowGuide(true), 600);
      }
    }, 120);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-white text-black px-6">

      {/* ✅ 添加图标 */}
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
          快速开始：{"\n"}
          1、点击侧边栏的 <code className="bg-gray-100 px-1 rounded">数据源</code>，
          可创建数据源和使用示例数据源{"\n"}
          2、将鼠标移动到数据源块上，点击
          <code className="bg-gray-100 px-1 rounded">快速新建数据源</code>，
          即可开始提问
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
