export interface Message {
  id: number;
  conversation_id: number;
  role: string;
  content: string;
  sql?: string;
  charts?: Record<string, any> | null;
  sample_data?: Record<string, any>[] | null;
  compute_code?: string;
  code_result?: string;
  created_at?: string;
}