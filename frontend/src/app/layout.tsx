import "./globals.css";
import { Providers } from "@/components/Providers";
import AuthCheck from "@/components/AuthCheck";
import AuthLayout from "@/components/AuthLayout";

export const metadata = {
  title: "VoloData",
  description: "基于大语言模型研发的智能数据分析助手，可以用自然语言进行查询和分析数据",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="flex h-screen">
        <Providers>
          <AuthCheck>
            <AuthLayout>{children}</AuthLayout>
          </AuthCheck>
        </Providers>
      </body>
    </html>
  );
}