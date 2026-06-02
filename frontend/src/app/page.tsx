"use client";

import { useState, useEffect, useCallback } from "react";
import { ChatInterface } from "@/components/chat-interface";

export default function ChatPage() {
  const [conversationId, setConversationId] = useState<string | undefined>();

  useEffect(() => {
    const stored = sessionStorage.getItem("activeConversationId");
    if (stored) {
      setConversationId(stored);
      sessionStorage.removeItem("activeConversationId");
    }
  }, []);

  const handleConversationChange = useCallback((id: string) => {
    if (id) setConversationId(id);
    else setConversationId(undefined);
  }, []);

  return (
    <ChatInterface
      key={conversationId ?? "new"}
      conversationId={conversationId}
      onConversationChange={handleConversationChange}
    />
  );
}
