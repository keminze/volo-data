export interface DataSource {
  id: number;
  name: string;
  db_type: string;        // 后端字段名为 db_type
  db_description?: string;
  created_at?: string;
}