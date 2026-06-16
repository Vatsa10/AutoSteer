"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getAgents,
  getDepartments,
  getConversations,
  getConversationMessages,
  getSystemStatus,
  type ChatResponse,
  type ConversationMessage,
} from "./api";
import { useToastStore } from "./store";

// ── Agents ───────────────────────────────────────────────────────

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: getAgents,
    staleTime: 60_000,
  });
}

export function useDepartments() {
  return useQuery({
    queryKey: ["departments"],
    queryFn: getDepartments,
    staleTime: 60_000,
  });
}

// ── Conversations ────────────────────────────────────────────────

export function useConversations() {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: getConversations,
    staleTime: 10_000,
    refetchInterval: 15_000, // auto-refresh every 15s
  });
}

export function useConversationMessages(conversationId: string | undefined) {
  return useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => getConversationMessages(conversationId!),
    enabled: !!conversationId,
    staleTime: 10_000,
  });
}

// ── Chat mutation ────────────────────────────────────────────────

interface FileAttachment { filename: string; content: string; mime_type: string; }

interface SendMessageVars {
  message: string;
  conversationId?: string;
  targetAgent?: string;
  fileIds?: string[];
  files?: FileAttachment[];
}

export function useSendMessage() {
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);

  return useMutation({
    mutationFn: async ({ message, conversationId, targetAgent, fileIds, files }: SendMessageVars) => {
      const apiKey = process.env.NEXT_PUBLIC_API_KEY || "";
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (apiKey) headers["X-API-Key"] = apiKey;
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/chat`,
        {
          method: "POST",
          headers,
          body: JSON.stringify({
            message,
            conversation_id: conversationId,
            target_agent: targetAgent || null,
            file_ids: fileIds || null,
            files: files || null,
          }),
        },
      );
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Chat failed (${res.status}): ${errText}`);
      }
      return res.json() as Promise<ChatResponse>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (error: Error) => {
      addToast(error.message, "error");
    },
  });
}

// ── System status ────────────────────────────────────────────────

export function useSystemStatus() {
  return useQuery({
    queryKey: ["status"],
    queryFn: getSystemStatus,
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}
