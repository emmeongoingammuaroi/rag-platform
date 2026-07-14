import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useConversationStore } from "../stores/conversations";
import { ChatMessages } from "../components/chat/ChatMessages";
import { ChatInput } from "../components/chat/ChatInput";
import { MessageSquare } from "lucide-react";

export function ChatPage() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const {
    currentConversation,
    isLoading,
    isSending,
    fetchConversation,
    sendMessage,
    createConversation,
    clearCurrent,
  } = useConversationStore();

  useEffect(() => {
    if (conversationId) {
      fetchConversation(conversationId);
    } else {
      clearCurrent();
    }
    return () => clearCurrent();
  }, [conversationId, fetchConversation, clearCurrent]);

  const handleSend = async (content: string) => {
    if (!content.trim()) return;

    let activeId = conversationId;
    if (!activeId) {
      const conv = await createConversation(content.slice(0, 40));
      if (!conv) return;
      activeId = conv.id;
      navigate(`/chat/${activeId}`, { replace: true });
      // Fetch the new conversation to populate messages
      await useConversationStore.getState().fetchConversation(activeId);
    }
    await sendMessage(activeId, content);
  };

  // Empty state — no conversation selected
  if (!conversationId && !currentConversation) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md px-4">
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
              <MessageSquare size={24} className="text-gray-400" />
            </div>
            <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              Start a conversation
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Ask questions about your uploaded documents. The AI will retrieve
              relevant context and provide answers with citations.
            </p>
          </div>
        </div>
        <ChatInput onSend={handleSend} disabled={isSending} />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin h-6 w-6 border-2 border-gray-300 border-t-blue-600 rounded-full" />
        </div>
      ) : (
        <ChatMessages
          messages={currentConversation?.messages || []}
          isStreaming={isSending}
        />
      )}
      <ChatInput onSend={handleSend} disabled={isSending} />
    </div>
  );
}
