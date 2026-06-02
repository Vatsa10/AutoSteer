"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { History, MessageSquare, ChevronRight } from "lucide-react";
import { getConversations, getConversationMessages, type Conversation } from "@/lib/api";

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    getConversations()
      .then(setConversations)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function handleOpen(id: string) {
    sessionStorage.setItem("activeConversationId", id);
    router.push("/");
  }

  return (
    <div className="h-full flex flex-col">
      <div className="shrink-0 border-b border-warm-800/60 px-5 py-3.5 flex items-center gap-2.5">
        <History className="w-4 h-4 text-amber-500" />
        <h2 className="text-sm font-semibold text-warm-200">Conversation History</h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="text-center text-warm-500 py-12 text-sm">
            Loading conversations…
          </div>
        )}

        {!loading && conversations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center px-6">
            <div className="w-12 h-12 rounded-xl bg-warm-800/40 border border-warm-700/40 flex items-center justify-center mb-3">
              <MessageSquare className="w-5 h-5 text-warm-500" />
            </div>
            <p className="text-sm text-warm-400">No conversations yet</p>
            <p className="text-xs text-warm-500 mt-1">
              Send a message in the chat to create one.
            </p>
          </div>
        )}

        {conversations.map((conv) => (
          <button
            key={conv.id}
            onClick={() => handleOpen(conv.id)}
            className="w-full text-left px-5 py-3.5 border-b border-warm-800/40 hover:bg-warm-800/30 transition-colors flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-warm-800/60 border border-warm-700/50 flex items-center justify-center shrink-0 group-hover:border-amber-800/50 transition-colors">
              <MessageSquare className="w-3.5 h-3.5 text-warm-400 group-hover:text-amber-400 transition-colors" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-warm-200 truncate">
                {conv.title}
              </p>
              <p className="text-[11px] text-warm-500">
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
                  ? "bg-green-950/30 text-green-400 border-green-900/40"
                  : "bg-warm-800 text-warm-400 border-warm-700"
              }`}
            >
              {conv.status}
            </span>
            <ChevronRight className="w-4 h-4 text-warm-600 group-hover:text-warm-400 transition-colors" />
          </button>
        ))}
      </div>
    </div>
  );
}
