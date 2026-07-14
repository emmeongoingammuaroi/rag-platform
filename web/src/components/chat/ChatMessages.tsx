import { useEffect, useRef } from "react";
import { User, Bot } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import type { Message } from "../../lib/types";

interface ChatMessagesProps {
  messages: Message[];
  isStreaming: boolean;
}

export function ChatMessages({ messages, isStreaming }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {messages.map((message) => (
          <div key={message.id} className="flex gap-4">
            <div
              className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
                message.role === "user"
                  ? "bg-blue-600"
                  : "bg-gray-800 dark:bg-gray-700"
              }`}
            >
              {message.role === "user" ? (
                <User size={14} className="text-white" />
              ) : (
                <Bot size={14} className="text-white" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <MessageBubble message={message} />
            </div>
          </div>
        ))}

        {isStreaming && (
          <div className="flex gap-4">
            <div className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center bg-gray-800 dark:bg-gray-700">
              <Bot size={14} className="text-white" />
            </div>
            <div className="flex items-center gap-1 pt-2">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
