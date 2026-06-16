"use client";

import { useState, useCallback } from "react";
import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { deleteConversation } from "@/lib/api";
import { useToastStore, useChatStore } from "@/lib/store";
import { useRouter } from "next/navigation";

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: string;
}

interface ConversationListProps {
  conversations: ConversationSummary[];
  activeId?: string;
  onSelect: (id: string) => void;
  onNew: () => void;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

export function ConversationList({
  conversations,
  activeId,
  onSelect,
  onNew,
}: ConversationListProps) {
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);
  const reset = useChatStore((s) => s.reset);
  const router = useRouter();
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const handleDelete = useCallback(
    async (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      if (confirmId !== id) {
        setConfirmId(id);
        return;
      }
      setDeleting(id);
      try {
        await deleteConversation(id);
        queryClient.invalidateQueries({ queryKey: ["conversations"] });
        queryClient.invalidateQueries({ queryKey: ["messages"] });
        if (activeId === id) {
          reset();
          router.push("/chat");
        }
        addToast("Conversation deleted", "success");
      } catch {
        addToast("Failed to delete conversation", "error");
      } finally {
        setDeleting(null);
        setConfirmId(null);
      }
    },
    [confirmId, queryClient, activeId, router, addToast],
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
          Conversations
        </span>
        <button
          onClick={onNew}
          className="p-1 rounded-md text-slate-500 hover:text-blue-600 hover:bg-slate-100 transition-colors"
          aria-label="New conversation"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
        {conversations.length === 0 && (
          <p className="text-xs text-slate-400 px-3 py-4 text-center">
            No conversations yet. Send a message to start.
          </p>
        )}
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`w-full text-left rounded-lg text-sm transition-colors flex items-center gap-2 group border ${
              activeId === conv.id
                ? "bg-blue-50 text-blue-700 border-blue-200"
                : "text-slate-700 hover:text-slate-900 hover:bg-slate-100 border-transparent"
            }`}
          >
            <button
              onClick={() => {
                setConfirmId(null);
                onSelect(conv.id);
              }}
              className="flex items-center gap-2.5 flex-1 min-w-0 px-3 py-2"
            >
              <MessageSquare
                className={`w-3.5 h-3.5 shrink-0 ${
                  activeId === conv.id ? "text-blue-600" : "text-slate-400"
                }`}
              />
              <span className="truncate flex-1">{conv.title}</span>
              <span className="text-[10px] text-slate-400 shrink-0">
                {timeAgo(conv.updated_at)}
              </span>
            </button>
            <button
              onClick={(e) => handleDelete(e, conv.id)}
              disabled={deleting === conv.id}
              className={`shrink-0 px-2 py-2 rounded-r-lg transition-all ${
                confirmId === conv.id
                  ? "text-red-600 bg-red-50 hover:bg-red-100"
                  : "text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100"
              }`}
              title={confirmId === conv.id ? "Click again to confirm delete" : "Delete conversation"}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
