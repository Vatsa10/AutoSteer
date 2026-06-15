"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChatInterface } from "@/components/chat-interface";

function ChatPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const conversationId = searchParams.get("c") || undefined;

  return (
    <ChatInterface
      conversationId={conversationId}
      onConversationChange={(id) => {
        if (id) {
          router.replace(`/?c=${encodeURIComponent(id)}`, { scroll: false });
        } else {
          router.replace("/", { scroll: false });
        }
      }}
    />
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-full" />}>
      <ChatPageInner />
    </Suspense>
  );
}
