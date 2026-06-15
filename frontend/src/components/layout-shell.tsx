"use client";

import { Suspense } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { Sidebar } from "@/components/sidebar";

function LayoutShellInner({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const isBare = pathname.startsWith("/landing");
  const activeConversationId = pathname === "/" ? (searchParams.get("c") || undefined) : undefined;

  const handleSelectConversation = useCallback(
    (id: string) => {
      router.replace(`/?c=${encodeURIComponent(id)}`, { scroll: false });
    },
    [router],
  );

  const handleNewConversation = useCallback(() => {
    router.replace("/", { scroll: false });
  }, [router]);

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

export function LayoutShell({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={
      <div className="flex h-screen overflow-hidden">
        <aside className="w-64 border-r border-slate-200 bg-slate-50 shrink-0" />
        <main className="flex-1 overflow-hidden">{children}</main>
      </div>
    }>
      <LayoutShellInner>{children}</LayoutShellInner>
    </Suspense>
  );
}
