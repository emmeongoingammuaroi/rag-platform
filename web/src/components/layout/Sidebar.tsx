import { useEffect } from "react";
import { useNavigate, useParams, Link, useLocation } from "react-router-dom";
import {
  Plus,
  MessageSquare,
  FileText,
  LogOut,
  X,
} from "lucide-react";
import { useAuthStore } from "../../stores/auth";
import { useConversationStore } from "../../stores/conversations";
import { ThemeToggle } from "../ui/ThemeToggle";

interface SidebarProps {
  onClose: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { conversationId } = useParams();
  const { user, logout } = useAuthStore();
  const { conversations, fetchConversations, createConversation } =
    useConversationStore();

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const handleNewChat = async () => {
    const conv = await createConversation();
    if (conv) {
      navigate(`/chat/${conv.id}`);
      onClose();
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800">
      {/* Header */}
      <div className="flex items-center justify-between h-14 px-4 border-b border-gray-200 dark:border-gray-800">
        <h1 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">
          RAG Platform
        </h1>
        <button
          onClick={onClose}
          className="p-1 lg:hidden text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          <X size={18} />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <Plus size={16} />
          New Chat
        </button>
      </div>

      {/* Navigation */}
      <nav className="px-3 mb-2">
        <Link
          to="/documents"
          onClick={onClose}
          className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors ${
            location.pathname === "/documents"
              ? "bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
          }`}
        >
          <FileText size={16} />
          Documents
        </Link>
      </nav>

      {/* Conversations */}
      <div className="flex-1 overflow-y-auto px-3">
        <p className="px-3 py-1 text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wider">
          Chats
        </p>
        <div className="space-y-0.5 mt-1">
          {conversations.map((conv) => (
            <Link
              key={conv.id}
              to={`/chat/${conv.id}`}
              onClick={onClose}
              className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors truncate ${
                conversationId === conv.id
                  ? "bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              <MessageSquare size={14} className="shrink-0" />
              <span className="truncate">{conv.title}</span>
            </Link>
          ))}
        </div>
      </div>

      {/* User / Logout */}
      <div className="p-3 border-t border-gray-200 dark:border-gray-800">
        <div className="flex items-center justify-between px-3 py-2">
          <span className="text-sm text-gray-700 dark:text-gray-300 truncate">
            {user?.email}
          </span>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <button
              onClick={handleLogout}
              className="p-1.5 text-gray-500 hover:text-red-600 dark:hover:text-red-400 transition-colors"
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
