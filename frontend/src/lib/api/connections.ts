import { apiRequest } from "@/lib/api/request";

/**
 * 🧩 数据源类型定义
 */
export interface DataSourceResponse {
  /** 数据源ID */
  id: number;
  /** 数据源名称 */
  name: string;
  /** 数据源类型 (如 MySQL, PostgreSQL, CSV 等) */
  db_type: string;
  /** 数据源描述 */
  db_description?: string;
  /** 创建时间 */
  created_at?: string;
}

/**
 * 🟢 连接数据源，获取表列表
 */
export async function getTables(formData: FormData) {
  return apiRequest<{ message: string; tables: Array<Record<string,string>> }>("/connections/connect", {
    method: "POST",
    body: formData,
  });
}

/**
 * 🟢 创建数据源
 */
export async function createConnection(formData: FormData) {
  return apiRequest<{ message: string; connection_id: number }>("/connections/init", {
    method: "POST",
    body: formData,
  });
}

/**
 * 🟣 获取数据源列表
 */
export async function listConnections() {
  return apiRequest<DataSourceResponse[]>("/connections/list", {
    method: "GET",
  });
}

/**
 * 🟣 获取单个数据源信息
 */
export async function getConnectionInfo(connectionId: number) {
  return apiRequest<DataSourceResponse>(`/connections/info/${connectionId}`, {
    method: "GET",
  });
}

/**
 * 🔴 删除数据源
 */
export async function deleteConnection(connectionId: number) {
  return apiRequest<{ message: string }>(
    `/connections/disconnect/${connectionId}`,
    {
      method: "DELETE",
    }
  );
}

/**
 * 🔴 修改数据源信息
 */
export async function updateConnectionInfo(
  connectionId: number,
  request: { new_name?: string; new_description?: string },
) {
  return apiRequest<{ message: string }>(
    `/connections/update/${connectionId}`,
    {
      method: "POST",
      body: request,
    }
  );
}