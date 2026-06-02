"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState, useCallback } from "react";
import { Sidebar } from "@/components/sidebar";

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isBare = pathname.startsWith("/landing");

  const [activeConversationId, setActiveConversationId] = useState<string>();
  const router = useRouter();

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

  if (isBare) {
    return <>{children}</>;
  }

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
