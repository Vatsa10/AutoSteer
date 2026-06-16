"use client";

import { usePathname } from "next/navigation";
import { useCallback } from "react";
import { Sidebar } from "@/components/sidebar";
import { useChatStore } from "@/lib/store";

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isBare = pathname.startsWith("/landing");
  const conversationId = useChatStore((s) => s.conversationId);
  const reset = useChatStore((s) => s.reset);
  const setConversationId = useChatStore((s) => s.setConversationId);

  const handleSelectConversation = useCallback(
    (id: string) => { setConversationId(id); },
    [setConversationId],
  );

  const handleNewConversation = useCallback(() => {
    reset();
  }, [reset]);

  if (isBare) return <>{children}</>;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        activeConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
