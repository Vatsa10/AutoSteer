"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { UserButton } from "@clerk/nextjs";
import {
  MessageSquare,
  Users,
  History,
  Network,
  PanelLeftClose,
  PanelLeft,
  Loader2,
  Settings,
  LayoutTemplate,
  CheckSquare,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { ConversationList, type ConversationSummary } from "@/components/conversation-list";
import { useConversations } from "@/lib/hooks";
import { getPendingApprovals } from "@/lib/api";

const navItems = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/templates", label: "Templates", icon: LayoutTemplate },
  { href: "/agents", label: "Agents", icon: Users },
  { href: "/settings/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/conversations", label: "History", icon: History },
  { href: "/settings", label: "Settings", icon: Settings },
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

  // TanStack Query: auto-refreshes every 15s, invalidates on new messages
  const { data: conversations = [], isLoading } = useConversations();

  // Pending approvals count — refetch every 30s for the badge
  const { data: approvalData } = useQuery({
    queryKey: ["pendingApprovalsCount"],
    queryFn: getPendingApprovals,
    refetchInterval: 30_000,
    select: (data) => data.length,
  });
  const pendingCount = approvalData ?? 0;

  const summaries: ConversationSummary[] = conversations.map((c) => ({
    id: c.id,
    title: c.title,
    updated_at: c.updated_at,
    last_message: c.last_message,
  }));

  if (collapsed) {
    return (
      <aside className="w-14 border-r border-slate-200 bg-slate-50 flex flex-col items-center py-3 gap-1 shrink-0">
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-slate-100 transition-colors mb-2"
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
                  ? "bg-blue-50 text-blue-600 border border-blue-200"
                  : "text-slate-500 hover:text-slate-700 hover:bg-slate-100 border border-transparent"
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
    <aside className="w-64 border-r border-slate-200 bg-slate-50 flex flex-col shrink-0">
      {/* Brand */}
      <div className="px-4 py-3.5 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center">
              <Network className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 leading-tight">
                Raah
              </h1>
            </div>
          </Link>
          <button
            onClick={() => setCollapsed(true)}
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Nav */}
      <nav className="px-2 py-2 space-y-0.5 border-b border-slate-200">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-blue-50 text-blue-700 border border-blue-200"
                  : "text-slate-600 hover:text-slate-800 hover:bg-slate-100 border border-transparent"
              }`}
            >
              <Icon className="w-4 h-4" />
              {item.label}
              {item.href === "/settings/approvals" && pendingCount > 0 && (
                <span className="ml-auto text-[10px] font-bold bg-[#E61919] text-white px-1.5 py-0.5 leading-none">
                  {pendingCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Conversations list */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-4 h-4 text-slate-400 animate-spin" />
          </div>
        ) : (
          <ConversationList
            conversations={summaries}
            activeId={activeConversationId}
            onSelect={(id) => {
              onSelectConversation?.(id);
            }}
            onNew={() => onNewConversation?.()}
          />
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <div className="w-1.5 h-1.5 rounded-full bg-green-600" />
          43 agents
        </div>
        <UserButton />
      </div>
    </aside>
  );
}
