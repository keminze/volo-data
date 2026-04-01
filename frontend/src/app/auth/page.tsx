"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslation } from "react-i18next";
import { Database, Mail, Lock, User, LogIn, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [email, setEmail] = useState("");
  const router = useRouter();
  const { login, register, isLoading, error } = useAuthStore();
  const { t } = useTranslation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isLogin && password !== confirmPassword) {
      alert(t("auth.passwordMismatch"));
      return;
    }

    try {
      if (isLogin) {
        await login({ username, password });
      } else {
        await register({ username, password, email: email || undefined });
      }
      router.push("/");
    } catch (err) {
      // 错误已在 store 中处理
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setPassword("");
    setConfirmPassword("");
    setEmail("");
  };

  return (
    <div className="min-h-screen flex relative overflow-hidden bg-black">
      {/* 左侧装饰区域 */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 relative overflow-hidden">
        {/* 动态背景网格 */}
        <div className="absolute inset-0" style={{
          backgroundImage: `linear-gradient(rgba(56, 189, 248, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(56, 189, 248, 0.03) 1px, transparent 1px)`,
          backgroundSize: '60px 60px'
        }}></div>

        {/* 动态光效 */}
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute top-1/4 -left-20 w-80 h-80 bg-sky-500/20 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1.2, 1, 1.2],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1
          }}
          className="absolute bottom-1/4 -right-20 w-96 h-96 bg-sky-400/15 rounded-full blur-3xl"
        />

        {/* 浮动动画元素 */}
        {[...Array(6)].map((_, i) => (
          <motion.div
            key={i}
            animate={{
              y: [0, -20, 0],
              opacity: [0.3, 0.6, 0.3],
            }}
            transition={{
              duration: 3 + i * 0.5,
              repeat: Infinity,
              ease: "easeInOut",
              delay: i * 0.3
            }}
            className="absolute w-2 h-2 bg-sky-400/40 rounded-full"
            style={{
              left: `${20 + i * 12}%`,
              top: `${30 + (i % 3) * 20}%`,
            }}
          />
        ))}

        {/* 内容 */}
        <div className="relative z-10 flex flex-col justify-center px-16 text-white">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex items-center gap-4 mb-8"
          >
            <motion.div
              whileHover={{ scale: 1.05, rotate: 5 }}
              className="w-16 h-16 bg-sky-500/20 border border-sky-500/30 rounded-2xl flex items-center justify-center backdrop-blur-sm"
            >
              <Database size={36} className="text-sky-400" />
            </motion.div>
            <div>
              <h1 className="text-4xl font-bold text-white">VoloData</h1>
              <p className="text-sky-300/70 text-sm">智能数据分析助手</p>
            </div>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-3xl font-semibold mb-4 text-white"
          >
            {isLogin ? "欢迎回来" : "创建账户"}
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-slate-400 text-lg mb-8 max-w-md"
          >
            {isLogin
              ? "使用您的账户登录，继续使用智能数据分析助手"
              : "注册一个新账户，开始使用强大的数据分析功能"}
          </motion.p>

          {/* 特性列表 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="space-y-4"
          >
            {[
              { icon: Sparkles, text: "自然语言查询数据" },
              { icon: Sparkles, text: "智能 SQL 生成" },
              { icon: Sparkles, text: "可视化图表生成" },
              { icon: Sparkles, text: "多数据源支持" }
            ].map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: 0.4 + index * 0.1 }}
                className="flex items-center gap-3"
              >
                <feature.icon size={16} className="text-sky-400" />
                <span className="text-slate-300">{feature.text}</span>
              </motion.div>
            ))}
          </motion.div>
        </div>

        {/* 底部渐变过渡 */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent"></div>
      </div>

      {/* 右侧表单区域 */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-md"
        >
          <Card className="border-0 shadow-2xl shadow-slate-400/50">
            <CardHeader className="text-center pb-2">
              {/* 移动端 Logo */}
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4 }}
                className="mx-auto w-14 h-14 bg-slate-900 rounded-2xl flex items-center justify-center mb-4 lg:hidden"
              >
                <Database size={28} className="text-sky-400" />
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.1 }}
              >
                <CardTitle className="text-2xl font-bold text-slate-800">
                  {isLogin ? t("auth.login") : t("auth.register")}
                </CardTitle>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.15 }}
              >
                <CardDescription className="text-slate-500">
                  {isLogin ? t("auth.loginDesc") : t("auth.registerDesc")}
                </CardDescription>
              </motion.div>
            </CardHeader>

            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* 用户名 */}
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.4, delay: 0.2 }}
                  className="space-y-2"
                >
                  <label className="text-sm font-medium text-slate-700">
                    {t("auth.username")}
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <Input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder={t("auth.usernamePlaceholder")}
                      className="pl-10 h-11 border-slate-200 focus:border-sky-400 focus:ring-sky-100"
                      required
                    />
                  </div>
                </motion.div>

                {/* 邮箱 - 仅注册 */}
                {!isLogin && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-2"
                  >
                    <label className="text-sm font-medium text-slate-700">
                      {t("auth.email")}
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                      <Input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder={t("auth.emailPlaceholder")}
                        className="pl-10 h-11 border-slate-200 focus:border-sky-400 focus:ring-sky-100"
                      />
                    </div>
                  </motion.div>
                )}

                {/* 密码 */}
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.4, delay: 0.25 }}
                  className="space-y-2"
                >
                  <label className="text-sm font-medium text-slate-700">
                    {t("auth.password")}
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <Input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={t("auth.passwordPlaceholder")}
                      className="pl-10 h-11 border-slate-200 focus:border-sky-400 focus:ring-sky-100"
                      required
                    />
                  </div>
                </motion.div>

                {/* 确认密码 - 仅注册 */}
                {!isLogin && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-2"
                  >
                    <label className="text-sm font-medium text-slate-700">
                      {t("auth.confirmPassword")}
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                      <Input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder={t("auth.confirmPasswordPlaceholder")}
                        className="pl-10 h-11 border-slate-200 focus:border-sky-400 focus:ring-sky-100"
                        required
                      />
                    </div>
                  </motion.div>
                )}

                {/* 错误提示 */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-red-500 text-sm text-center p-3 bg-red-50 rounded-lg border border-red-100"
                  >
                    {error}
                  </motion.div>
                )}

                {/* 提交按钮 */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: 0.3 }}
                >
                  <Button
                    type="submit"
                    className="w-full h-11 bg-slate-900 hover:bg-slate-800 text-white text-base font-medium transition-all hover:shadow-lg hover:shadow-sky-500/20"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <span className="flex items-center gap-2">
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                        </svg>
                        {t("auth.loading")}
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <LogIn size={18} />
                        {isLogin ? t("auth.login") : t("auth.register")}
                      </span>
                    )}
                  </Button>
                </motion.div>
              </form>

              {/* 切换登录/注册 */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.4, delay: 0.35 }}
                className="mt-6 pt-6 border-t border-slate-200 text-center"
              >
                <p className="text-slate-600">
                  {isLogin ? t("auth.noAccount") : t("auth.hasAccount")}{" "}
                  <button
                    type="button"
                    onClick={toggleMode}
                    className="text-sky-500 hover:text-sky-600 font-medium hover:underline"
                  >
                    {isLogin ? t("auth.registerNow") : t("auth.loginNow")}
                  </button>
                </p>
              </motion.div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}