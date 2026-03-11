# =========================
# 1️⃣ 构建阶段
# =========================
FROM node:22.20.0-slim AS builder

# 设置工作目录
WORKDIR /app

# 复制依赖文件（package.json + lock 文件）
COPY package*.json ./
# 如果你使用 pnpm 或 yarn，请改为：
# COPY pnpm-lock.yaml ./
# COPY yarn.lock ./

# 安装依赖（使用 --frozen-lockfile 保证一致性）
RUN npm ci

# 复制所有源代码
COPY . .

# 构建 Next.js 项目
RUN npm run build

# =========================
# 2️⃣ 运行阶段
# =========================
FROM node:22.20.0-slim AS runner

WORKDIR /app

# 仅复制运行所需文件
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules

# 环境变量配置（Next.js 生产模式）
ENV NODE_ENV=production
ENV PORT=3000

# 暴露端口
EXPOSE 3000

# 运行 Next.js
CMD ["npm", "start"]