import { create } from "zustand";
import { api } from "../lib/api";
import type {
  Conversation,
  ConversationDetail,
  ConversationList,
  Message,
  SendMessageResponse,
} from "../lib/types";

interface ConversationState {
  conversations: Conversation[];
  currentConversation: ConversationDetail | null;
  isLoading: boolean;
  isSending: boolean;
  streamingContent: string;

  fetchConversations: () => Promise<void>;
  fetchConversation: (id: string) => Promise<void>;
  createConversation: (title?: string) => Promise<Conversation | null>;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (conversationId: string, content: string) => Promise<void>;
  clearCurrent: () => void;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversations: [],
  currentConversation: null,
  isLoading: false,
  isSending: false,
  streamingContent: "",

  fetchConversations: async () => {
    try {
      const data = await api.get<ConversationList>("/api/v1/conversations?page_size=50");
      set({ conversations: data.items });
    } catch {
      // silent
    }
  },

  fetchConversation: async (id) => {
    set({ isLoading: true });
    try {
      const data = await api.get<ConversationDetail>(`/api/v1/conversations/${id}`);
      set({ currentConversation: data, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  createConversation: async (title) => {
    try {
      const conv = await api.post<Conversation>("/api/v1/conversations", {
        title: title || "New Chat",
      });
      set((s) => ({ conversations: [conv, ...s.conversations] }));
      return conv;
    } catch {
      return null;
    }
  },

  deleteConversation: async (id) => {
    try {
      await api.delete(`/api/v1/conversations/${id}`);
      set((s) => ({
        conversations: s.conversations.filter((c) => c.id !== id),
        currentConversation:
          s.currentConversation?.id === id ? null : s.currentConversation,
      }));
    } catch {
      // silent
    }
  },

  sendMessage: async (conversationId, content) => {
    set({ isSending: true, streamingContent: "" });

    // Add user message optimistically
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      sources: null,
      created_at: new Date().toISOString(),
    };

    set((s) => ({
      currentConversation: s.currentConversation
        ? {
            ...s.currentConversation,
            messages: [...s.currentConversation.messages, userMessage],
          }
        : null,
    }));

    try {
      const data = await api.post<SendMessageResponse>(
        `/api/v1/conversations/${conversationId}/messages`,
        { content },
      );

      // Replace streaming with final message
      set((s) => ({
        isSending: false,
        streamingContent: "",
        currentConversation: s.currentConversation
          ? {
              ...s.currentConversation,
              messages: [...s.currentConversation.messages, data.message],
            }
          : null,
      }));

      // Update conversation title in list if it was "New Chat"
      const conv = get().conversations.find((c) => c.id === conversationId);
      if (conv && conv.title === "New Chat") {
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId
              ? { ...c, title: content.slice(0, 40) }
              : c,
          ),
        }));
      }
    } catch {
      set({ isSending: false, streamingContent: "" });
    }
  },

  clearCurrent: () => {
    set({ currentConversation: null, streamingContent: "" });
  },
}));
