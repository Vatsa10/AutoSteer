"use client";

import { useState, useCallback } from "react";
import { Sidebar } from "@/components/sidebar";
import { useRouter, usePathname } from "next/navigation";

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const [activeConversationId, setActiveConversationId] = useState<string>();
  const router = useRouter();
  const pathname = usePathname();

  const handleSelectConversation = useCallback(
    (id: string) => {
      setActiveConversationId(id);
      sessionStorage.setItem("activeConversationId", id);
      if (pathname !== "/") router.push("/");
    },
    [router, pathname],
  );

  const handleNewConversation = useCallback(() => {
    setActiveConversationId(undefined);
    sessionStorage.removeItem("activeConversationId");
    if (pathname !== "/") router.push("/");
  }, [router, pathname]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
      />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
