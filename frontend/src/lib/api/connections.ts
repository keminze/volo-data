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
 * 🟢 创建（连接）数据源
 * @param formData 表单数据（包含数据库连接信息）
 * @returns 返回新建连接的 message 与 connection_id
 *
 * ⚠️ 注意：该接口使用 multipart/form-data 上传，因此 `apiRequest` 不需要自动序列化 JSON。
 */
export async function getTables(formData: FormData) {
  return apiRequest<{ message: string; tables: Array<Record<string,string>> }>("/connections/connect", {
    method: "POST",
    body: formData,
  });
}


/**
 * 🟢 创建（连接）数据源
 * @param formData 表单数据（包含数据库连接信息）
 * @returns 返回新建连接的 message 与 connection_id
 *
 * ⚠️ 注意：该接口使用 multipart/form-data 上传，因此 `apiRequest` 不需要自动序列化 JSON。
 */
export async function createConnection(formData: FormData) {
  return apiRequest<{ message: string; connection_id: number }>("/connections/init", {
    method: "POST",
    body: formData,
  });
}

/**
 * 🟣 获取数据源列表
 * @param userId 当前用户ID（默认1）
 */
export async function listConnections(userId: string) {
  return apiRequest<DataSourceResponse[]>(`/connections/list?user_id=${userId}`, {
    method: "GET",
  });
}

/**
 * 🟣 获取单个数据源信息
 * @param userId 当前用户ID（默认1）
 * @param connectionId 数据源ID
 */
export async function getConnectionInfo(connectionId: number, userId: string) {
  return apiRequest<DataSourceResponse>(`/connections/info/${connectionId}?user_id=${userId}`, {
    method: "GET",
  });
}

/**
 * 🔴 删除（断开）数据源
 * @param connectionId 数据源ID
 * @param userId 当前用户ID（默认1）
 */
export async function deleteConnection(
  connectionId: number,
  userId: string
) {
  return apiRequest<{ message: string }>(
    `/connections/disconnect/${connectionId}?user_id=${userId}`,
    {
      method: "DELETE",
    }
  );
}

/**
 * 🔴 修改数据源信息
 * @param connectionId 数据源ID
 * @param request 更新请求体
 */
export async function updateConnectionInfo(
  connectionId: number,
  request: { user_id?: string; new_name?: string; new_description?: string },
) {
  return apiRequest<{ message: string }>(
    `/connections/update/${connectionId}`,
    {
      method: "POST",
      body: request,
    }
  );
}