export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}

export interface Document {
  id: string;
  title: string;
  content: string;
  file_path: string | null;
  file_type: string | null;
  content_hash: string | null;
  user_id: string;
  chunk_count: number;
  embedding_status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  updated_at: string;
}

export interface DocumentList {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationList {
  items: Conversation[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  model: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface SendMessageResponse {
  conversation_id: string;
  assistant_message: Message;
}
