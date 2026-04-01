export const API_BASE = process.env.NEXT_PUBLIC_BACKEND_API_BASE!;
const API_KEY = process.env.NEXT_PUBLIC_BACKEND_API_KEY; // ✅ 从环境变量读取 API key

// 用于在请求时获取 token
let tokenGetter: (() => string | null) | null = null;

export function setTokenGetter(getter: () => string | null) {
  tokenGetter = getter;
}

export function getToken(): string | null {
  // 优先使用 tokenGetter
  if (tokenGetter) {
    const token = tokenGetter();
    if (token) return token;
  }
  // 备选：从 localStorage 直接读取（处理 persist 加载延迟）
  if (typeof window !== "undefined") {
    try {
      const stored = localStorage.getItem("auth-storage");
      if (stored) {
        const parsed = JSON.parse(stored);
        return parsed.state?.token || null;
      }
    } catch {}
  }
  return null;
}

export type ApiRequestOptions = {
  method?: string;
  headers?: Record<string, string>;
  body?: any;
  // 你可以进一步添加信号、credentials 等字段
  signal?: AbortSignal | null;
  useAuth?: boolean; // 是否使用 JWT 认证，默认 true
};

/**
 * 通用请求封装
 * - 自动把普通对象 body 转为 JSON 字符串
 * - 透传 FormData（文件上传）
 * - 将最终的 fetch 请求的 body 强制为 BodyInit | undefined，避免 TS 报错
 */
export async function apiRequest<T = any>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const method = options.method?.toUpperCase() ?? "GET";

  // 拷贝 headers（不会修改外部传入对象）
  const headers: Record<string, string> = { ...(options.headers || {}) };

  // console.log(process.env.NEXT_PUBLIC_BACKEND_API_KEY);

  // JWT 认证优先于 API Key
  const useAuth = options.useAuth !== false;
  if (useAuth) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  // 如果没有 JWT token，使用 API Key 作为备选
  if (!headers["Authorization"] && API_KEY) {
    headers["x-api-key"] = API_KEY;
  } else if (!headers["Authorization"] && !API_KEY) {
    console.warn("[apiRequest] 环境变量 NEXT_PUBLIC_BACKEND_API_KEY 未设置！");
  }

  // 处理 body -> finalBody 必须是 BodyInit | undefined
  let finalBody: BodyInit | undefined = undefined;

  if (options.body !== undefined && options.body !== null) {
    // 如果传入的是 FormData（文件上传），直接传
    if (typeof FormData !== "undefined" && options.body instanceof FormData) {
      finalBody = options.body;
      // 删除 Content-Type 让浏览器自动设置 multipart/form-data boundary
      if (headers["Content-Type"]) delete headers["Content-Type"];
    } else if (options.body instanceof URLSearchParams) {
      finalBody = options.body;
      headers["Content-Type"] = headers["Content-Type"] ?? "application/x-www-form-urlencoded;charset=UTF-8";
    } else if (typeof options.body === "string" || options.body instanceof Blob) {
      finalBody = options.body as BodyInit;
      headers["Content-Type"] = headers["Content-Type"] ?? "text/plain;charset=UTF-8";
    } else {
      // 普通对象 -> JSON
      finalBody = JSON.stringify(options.body);
      headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
    }
  }

  // console.log("[apiRequest] 请求：", headers);

  const res = await fetch(url, {
    method,
    headers,
    body: finalBody,
    signal: options.signal ?? undefined,
  });

  const contentType = res.headers.get("content-type") || "";

  const text = await res.text();

  if (!res.ok) {
    // 尽量返回可读的错误信息
    let parsed: any = text;
    try {
      parsed = contentType.includes("application/json") ? JSON.parse(text) : text;
    } catch {
      parsed = text;
    }
    throw new Error(`Request failed ${res.status}: ${JSON.stringify(parsed)}`);
  }

  // 返回解析：优先 JSON，否则返回文本
  if (contentType.includes("application/json")) {
    return JSON.parse(text) as T;
  }
  return text as T;
}