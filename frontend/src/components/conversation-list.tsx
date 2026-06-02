"use client";

import { MessageSquare, Plus } from "lucide-react";

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
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2">
        <span className="text-xs font-medium text-warm-400 uppercase tracking-wider">
          Conversations
        </span>
        <button
          onClick={onNew}
          className="p-1 rounded-md text-warm-400 hover:text-amber-400 hover:bg-warm-800/60 transition-colors"
          aria-label="New conversation"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
        {conversations.length === 0 && (
          <p className="text-xs text-warm-500 px-3 py-4 text-center">
            No conversations yet. Send a message to start.
          </p>
        )}
        {conversations.map((conv) => (
          <button
            key={conv.id}
            onClick={() => onSelect(conv.id)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center gap-2.5 group ${
              activeId === conv.id
                ? "bg-amber-950/30 text-amber-200 border border-amber-900/40"
                : "text-warm-300 hover:text-warm-100 hover:bg-warm-800/40 border border-transparent"
            }`}
          >
            <MessageSquare
              className={`w-3.5 h-3.5 shrink-0 ${
                activeId === conv.id ? "text-amber-500" : "text-warm-500"
              }`}
            />
            <span className="truncate flex-1">{conv.title}</span>
            <span className="text-[10px] text-warm-500 shrink-0">
              {timeAgo(conv.updated_at)}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
