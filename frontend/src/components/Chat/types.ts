export interface ToolCallRecord {
  id: number;
  tool_name: string;
  tool_args?: Record<string, any>;
  tool_result?: string;
  created_at?: string;
}

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
  tool_calls?: ToolCallRecord[] | null;
  created_at?: string;
}