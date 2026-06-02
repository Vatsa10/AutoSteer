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
      <div className="shrink-0 border-b border-slate-200 px-5 py-3.5 flex items-center gap-2.5">
        <History className="w-4 h-4 text-blue-600" />
        <h2 className="text-sm font-semibold text-slate-800">Conversation History</h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="text-center text-slate-500 py-12 text-sm">
            Loading conversations…
          </div>
        )}

        {!loading && conversations.length === 0 && (
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

        {conversations.map((conv) => (
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
