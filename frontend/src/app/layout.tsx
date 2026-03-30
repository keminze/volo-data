import "./globals.css";
import Sidebar from "@/components/Sidebar/Sidebar";
import { Providers } from "@/components/Providers";

export const metadata = {
  title: "VoloData",
  description: "基于大语言模型研发的智能数据分析助手，可以用自然语言进行查询和分析数据",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="flex h-screen">
        <Providers>
          {/* 左侧侧边栏 */}
          <Sidebar />
          {/* 右侧内容区 */}
          <main className="flex-1 bg-gray-50">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
