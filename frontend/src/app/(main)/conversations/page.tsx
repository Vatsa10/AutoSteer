"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { History, MessageSquare, ChevronRight, Loader2, Search, AlertCircle } from "lucide-react";
import { useConversations } from "@/lib/hooks";
import { useChatStore } from "@/lib/store";

export default function ConversationsPage() {
  const [search, setSearch] = useState("");
  const router = useRouter();
  const setConversationId = useChatStore((s) => s.setConversationId);

  const { data: conversations = [], isLoading, error } = useConversations();

  const filtered = useMemo(() => {
    if (!search.trim()) return conversations;
    const q = search.toLowerCase();
    return conversations.filter((c) =>
      c.title.toLowerCase().includes(q),
    );
  }, [conversations, search]);

  function handleOpen(id: string) {
    setConversationId(id);
    router.push("/chat");
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 border-b border-slate-200 px-5 py-3.5 flex items-center gap-3">
        <History className="w-4 h-4 text-blue-600" />
        <h2 className="text-sm font-semibold text-slate-800">Conversation History</h2>
        {!isLoading && conversations.length > 0 && (
          <span className="text-xs text-slate-400">{conversations.length} total</span>
        )}
      </div>

      {/* Search */}
      <div className="shrink-0 px-4 py-3 border-b border-slate-100">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search conversations…"
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400 transition-colors"
          />
          {search && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">
              {filtered.length} of {conversations.length}
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex items-center justify-center py-16 gap-2 text-slate-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Loading conversations…</span>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center py-16 text-center px-6 gap-3">
            <AlertCircle className="w-8 h-8 text-red-500" />
            <div>
              <p className="text-sm text-slate-700">Failed to load conversations</p>
              <p className="text-xs text-slate-400 mt-1">Check that the backend is running on port 8000.</p>
            </div>
          </div>
        )}

        {!isLoading && !error && filtered.length === 0 && conversations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center px-6">
            <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center mb-3">
              <MessageSquare className="w-5 h-5 text-slate-400" />
            </div>
            <p className="text-sm text-slate-500">No conversations yet</p>
            <p className="text-xs text-slate-400 mt-1">
              Send a message in the chat to create one.
            </p>
          </div>
        )}

        {!isLoading && !error && filtered.length === 0 && conversations.length > 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center px-6">
            <Search className="w-8 h-8 text-slate-300 mb-3" />
            <p className="text-sm text-slate-500">No conversations match "{search}"</p>
          </div>
        )}

        {filtered.map((conv) => (
          <button
            key={conv.id}
            onClick={() => handleOpen(conv.id)}
            className="w-full text-left px-5 py-3.5 border-b border-slate-100 hover:bg-slate-50 transition-colors flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0 group-hover:border-blue-300 transition-colors">
              <MessageSquare className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 transition-colors" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">
                {conv.title}
              </p>
              <p className="text-[11px] text-slate-400">
                {new Date(conv.created_at).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded-sm border ${
                conv.status === "active"
                  ? "bg-green-50 text-green-600 border-green-200"
                  : "bg-slate-100 text-slate-500 border-slate-200"
              }`}
            >
              {conv.status}
            </span>
            <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-500 transition-colors" />
          </button>
        ))}
      </div>
    </div>
  );
}
