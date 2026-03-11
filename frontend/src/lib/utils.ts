import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * 生成 UUID v4
 * @returns {string} 形如 "550e8400-e29b-41d4-a716-446655440000" 的 UUID
 */
function generateUUID(): string {
  if (crypto && crypto.randomUUID) {
    // ✅ 现代浏览器内置的安全UUID生成
    return crypto.randomUUID();
  }
  // ✅ 手动生成 fallback
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (crypto.getRandomValues(new Uint8Array(1))[0] % 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * 从 localStorage 获取 UUID；若不存在则自动生成并保存
 * @param {string} key - 存储的 key 名，默认 "user_uuid"
 * @returns {string} UUID
 */
export function getOrCreateUUID(key: string = "user_uuid"): string {
  if (typeof window === "undefined" || typeof localStorage === "undefined") {
    // SSR 或 Node 环境下，返回一个临时 UUID
    return generateUUID();
  }

  let uuid = localStorage.getItem(key);
  if (!uuid) {
    uuid = generateUUID();
    localStorage.setItem(key, uuid);
  }
  return uuid;
}

/**
 * 清除保存的 UUID（可选）
 * @param {string} key
 */
export function clearUUID(key: string = "user_uuid") {
  if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
    localStorage.removeItem(key);
  }
}
