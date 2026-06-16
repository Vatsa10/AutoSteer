"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ChatInterface } from "@/components/chat-interface";

function ChatPageInner() {
  const searchParams = useSearchParams();
  const initialConversationId = searchParams.get("c") || undefined;

  return <ChatInterface initialConversationId={initialConversationId} />;
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-full" />}>
      <ChatPageInner />
    </Suspense>
  );
}
