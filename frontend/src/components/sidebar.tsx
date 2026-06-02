"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import {
  MessageSquare,
  Users,
  History,
  Network,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import { ConversationList, type ConversationSummary } from "@/components/conversation-list";
import { getConversations } from "@/lib/api";

const navItems = [
  { href: "/", label: "Chat", icon: MessageSquare },
  { href: "/agents", label: "Agents", icon: Users },
  { href: "/conversations", label: "History", icon: History },
];

interface SidebarProps {
  activeConversationId?: string;
  onSelectConversation?: (id: string) => void;
  onNewConversation?: () => void;
}

export function Sidebar({
  activeConversationId,
  onSelectConversation,
  onNewConversation,
}: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);

  const refreshConversations = useCallback(async () => {
    try {
      const data = await getConversations();
      setConversations(
        data.map((c) => ({
          id: c.id,
          title: c.title,
          updated_at: c.updated_at,
        })),
      );
    } catch {
      // Backend not available
    }
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  if (collapsed) {
    return (
      <aside className="w-14 border-r border-warm-800/60 bg-warm-900/80 flex flex-col items-center py-3 gap-1 shrink-0">
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 rounded-lg text-warm-400 hover:text-amber-400 hover:bg-warm-800/60 transition-colors mb-2"
          aria-label="Expand sidebar"
        >
          <PanelLeft className="w-4 h-4" />
        </button>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`p-2 rounded-lg transition-colors ${
                isActive
                  ? "bg-amber-950/30 text-amber-400 border border-amber-900/40"
                  : "text-warm-400 hover:text-warm-200 hover:bg-warm-800/40 border border-transparent"
              }`}
              title={item.label}
            >
              <Icon className="w-4 h-4" />
            </Link>
          );
        })}
      </aside>
    );
  }

  return (
    <aside className="w-64 border-r border-warm-800/60 bg-warm-900/80 flex flex-col shrink-0">
      {/* Brand */}
      <div className="px-4 py-3.5 border-b border-warm-800/60">
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-amber-950/40 border border-amber-800/40 flex items-center justify-center">
              <Network className="w-4 h-4 text-amber-500" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-warm-100 leading-tight">
                AutoSteer
              </h1>
            </div>
          </Link>
          <button
            onClick={() => setCollapsed(true)}
            className="p-1.5 rounded-md text-warm-500 hover:text-warm-300 hover:bg-warm-800/60 transition-colors"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Nav */}
      <nav className="px-2 py-2 space-y-0.5 border-b border-warm-800/60">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-amber-950/30 text-amber-200 border border-amber-900/40"
                  : "text-warm-400 hover:text-warm-200 hover:bg-warm-800/40 border border-transparent"
              }`}
            >
              <Icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Conversations list */}
      <div className="flex-1 overflow-hidden">
        <ConversationList
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={(id) => {
            onSelectConversation?.(id);
          }}
          onNew={() => onNewConversation?.()}
        />
      </div>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-warm-800/60">
        <div className="flex items-center gap-2 text-xs text-warm-500">
          <div className="w-1.5 h-1.5 rounded-full bg-green-600" />
          42 agents across 12 departments
        </div>
      </div>
    </aside>
  );
}
