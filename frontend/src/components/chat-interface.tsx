"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Network, Loader2, Paperclip, X, FileText, Image } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useQueryClient } from "@tanstack/react-query";
import { RoutingPath } from "@/components/routing-path";
import { AgentSelector } from "@/components/agent-selector";
import { useChatStore, type RoutingEvent, type RoutingStage } from "@/lib/store";
import { useConversationMessages, useSendMessage } from "@/lib/hooks";
import { useToastStore } from "@/lib/store";
import { createChatWebSocket, sendWSMessage, type WSEvent } from "@/lib/websocket";
import { Onboarding } from "@/components/onboarding";

interface FileAttachment { filename: string; content: string; mime_type: string; }

interface ChatInterfaceProps {
  initialConversationId?: string;
}

export function ChatInterface({ initialConversationId }: ChatInterfaceProps) {
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);

  const messages = useChatStore((s) => s.messages);
  const setMessages = useChatStore((s) => s.setMessages);
  const addMessage = useChatStore((s) => s.addMessage);
  const appendContent = useChatStore((s) => s.appendContent);
  const conversationId = useChatStore((s) => s.conversationId);
  const setConversationId = useChatStore((s) => s.setConversationId);
  const targetAgent = useChatStore((s) => s.targetAgent);
  const setTargetAgent = useChatStore((s) => s.setTargetAgent);
  const routingStage = useChatStore((s) => s.routingStage);
  const setRoutingStage = useChatStore((s) => s.setRoutingStage);
  const routingEvents = useChatStore((s) => s.routingEvents);
  const addRoutingEvent = useChatStore((s) => s.addRoutingEvent);
  const clearRoutingEvents = useChatStore((s) => s.clearRoutingEvents);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const setIsStreaming = useChatStore((s) => s.setIsStreaming);
  const reset = useChatStore((s) => s.reset);

  const [input, setInput] = useState("");
  const [wsMode, setWsMode] = useState(true);
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const loadedOnce = useRef(false);
  // Stable ref to avoid sendMessageMutation recreating sendViaWebSocket every render.
  const sendMutationRef = useRef<ReturnType<typeof useSendMessage> | null>(null);

  // ── Deep-link + template prompt ──────────────────────────────
  useEffect(() => {
    if (initialConversationId && !loadedOnce.current) {
      loadedOnce.current = true;
      setConversationId(initialConversationId);
    }
    const templatePrompt = sessionStorage.getItem("autosteer_template_prompt");
    if (templatePrompt) {
      setInput(templatePrompt);
      sessionStorage.removeItem("autosteer_template_prompt");
    }
  }, [initialConversationId, setConversationId, setInput]);

  // ── Clear messages when switching conversations ──────────────
  useEffect(() => {
    setMessages([]);
  }, [conversationId, setMessages]);

  // ── Load conversation history ────────────────────────────────
  const { data: historyMessages, isLoading: isLoadingHistory } =
    useConversationMessages(conversationId);

  useEffect(() => {
    if (historyMessages && historyMessages.length > 0 && conversationId) {
      setMessages(
        historyMessages.map((m) => ({
          role: (m.message_type === "request" ? "user" : "assistant") as "user" | "assistant",
          content: m.content,
          agent: m.from_agent !== "user" ? m.from_agent : null,
          department: null,
          model: null,
        }))
      );
    }
  }, [historyMessages, conversationId, setMessages]);

  // ── Scroll ───────────────────────────────────────────────────
  const isHistoryLoad = useRef(false);
  useEffect(() => {
    if (isLoadingHistory) { isHistoryLoad.current = true; return; }
    if (isHistoryLoad.current && !isLoadingHistory) {
      isHistoryLoad.current = false;
      messagesEndRef.current?.scrollIntoView({ behavior: "instant" as ScrollBehavior });
      return;
    }
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, routingEvents, isLoadingHistory]);

  useEffect(() => { inputRef.current?.focus(); }, []);
  useEffect(() => { return () => { wsRef.current?.close(); }; }, []);

  // ── File picker ──────────────────────────────────────────────
  async function handleFilePick(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      const file = files[0];
      const reader = new FileReader();
      const base64 = await new Promise<string>((resolve, reject) => {
        reader.onload = () => { const r = reader.result as string; const c = r.indexOf(","); resolve(c >= 0 ? r.slice(c + 1) : r); };
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsDataURL(file);
      });
      setAttachments((prev) => [...prev, { filename: file.name, content: base64, mime_type: file.type || "application/octet-stream" }]);
      // Sync document to memory store
      try {
        const stored = localStorage.getItem("autosteer_memory");
        const mem = stored ? JSON.parse(stored) : { facts: [], documents: [], summary: "" };
        mem.documents.push({ filename: file.name, preview: "", char_count: file.size });
        localStorage.setItem("autosteer_memory", JSON.stringify(mem));
      } catch {}
    } catch (err) {
      addToast(err instanceof Error ? err.message : "Failed to read file", "error");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function removeAttachment(index: number) {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  }

  // ── REST mutation ────────────────────────────────────────────
  const sendMessageMutation = useSendMessage();
  sendMutationRef.current = sendMessageMutation;

  // ── WebSocket send ───────────────────────────────────────────
  const sendViaWebSocket = useCallback(
    (message: string, fileIds: string[], convId?: string, tgtAgent?: string, files?: FileAttachment[]) => {
      // Close any prior WebSocket before opening a new one.
      if (wsRef.current) {
        try { wsRef.current.close(); } catch {}
        wsRef.current = null;
      }
      clearRoutingEvents();
      setIsStreaming(true);
      const ws = createChatWebSocket({
        onEvent: (event: WSEvent) => {
          switch (event.type) {
            case "routing":
              setRoutingStage(event.stage as RoutingStage);
              addRoutingEvent({ type: event.stage as RoutingEvent["type"], label: event.stage || "", detail: event.department || event.agent });
              break;
            case "token": appendContent(event.content); break;
            case "metadata":
              if (event.conversation_id && !convId) setConversationId(event.conversation_id);
              break;
            case "error": addToast(event.message, "error"); setIsStreaming(false); setRoutingStage(""); break;
            case "done": setIsStreaming(false); setRoutingStage(""); queryClient.invalidateQueries({ queryKey: ["conversations"] }); break;
          }
        },
        onError: () => {
          setWsMode(false); setIsStreaming(false); setRoutingStage("");
          const m = sendMutationRef.current;
          if (!m) return;
          m.mutate(
            { message, conversationId: convId, targetAgent: tgtAgent, fileIds, files },
            { onSuccess: (data) => { appendContent(data.response); if (data.conversation_id && !convId) setConversationId(data.conversation_id); } },
          );
        },
        onClose: (error) => {
          // Only reset streaming if the WS closed unexpectedly (not after a clean "done" event).
          if (error) { setIsStreaming(false); setRoutingStage(""); setWsMode(false); }
        },
      });
      wsRef.current = ws;
      ws.onopen = () => { sendWSMessage(ws, message, convId, tgtAgent, fileIds, files); };
    },
    [clearRoutingEvents, setIsStreaming, setRoutingStage, addRoutingEvent, appendContent, setConversationId, addToast, queryClient],
  );

  // ── Submit ───────────────────────────────────────────────────
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if ((!input.trim() && attachments.length === 0) || isStreaming || sendMessageMutation.isPending) return;
    const userMessage = input.trim() || "Analyze the attached files.";
    const currentAttachments = [...attachments];
    const attachLabel = currentAttachments.length > 0 ? `\n[Attached: ${currentAttachments.map((a) => a.filename).join(", ")}]` : "";
    setInput(""); setAttachments([]);
    addMessage({ role: "user", content: userMessage + attachLabel });

    if (wsMode) {
      addMessage({ role: "assistant", content: "", agent: targetAgent });
      sendViaWebSocket(userMessage, [], conversationId, targetAgent ?? undefined, currentAttachments);
    } else {
      setIsStreaming(true); setRoutingStage("classifying");
      addMessage({ role: "assistant", content: "" });
      sendMessageMutation.mutate(
        { message: userMessage, conversationId, targetAgent: targetAgent ?? undefined, files: currentAttachments.length > 0 ? currentAttachments : undefined },
        {
          onSuccess: (data) => {
            setIsStreaming(false); setRoutingStage("");
            setMessages(useChatStore.getState().messages.slice(0, -1).concat({ role: "assistant", content: data.response, agent: data.agent, department: data.routed_to, model: data.model }));
            if (data.conversation_id && !conversationId) setConversationId(data.conversation_id);
          },
          onError: () => { setIsStreaming(false); setRoutingStage(""); },
        },
      );
    }
  }

  function handleNewConversation() { reset(); setInput(""); }

  return (
    <>
      <Onboarding onComplete={() => {}} />
      <div className="flex flex-col h-full">
      <div className="shrink-0 border-b border-slate-200 px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className={`w-2 h-2 rounded-full ${isStreaming ? "bg-blue-600 animate-pulse-glow" : "bg-green-500"}`} />
          <span className="text-sm font-medium text-slate-800">
            {isLoadingHistory ? "Loading..." : conversationId ? "Conversation" : "New Conversation"}
          </span>
        </div>
        {messages.length > 0 && (
          <button onClick={handleNewConversation} className="text-xs text-slate-500 hover:text-blue-600 transition-colors">New chat</button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {!isLoadingHistory && messages.length === 0 && !conversationId && (
          null
        )}
        {!isLoadingHistory && messages.length === 0 && conversationId && (
          <div className="flex flex-col items-center justify-center h-full text-center px-6">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center mb-5">
              <Network className="w-7 h-7 text-blue-600" />
            </div>
            <h2 className="text-lg font-semibold text-slate-800 mb-2">AutoSteer</h2>
            <p className="text-sm text-slate-500 max-w-md">Send a message and watch it route through the Master Orchestrator to the most qualified agent across 12 departments and 42 specialists.</p>
            <div className="mt-6 grid grid-cols-2 gap-2 w-full max-w-sm">
              {["Research the latest transformer architectures", "Design a new onboarding flow for enterprise customers", "Draft a sales proposal for Acme Corp", "Review my API for security vulnerabilities"].map((s) => (
                <button key={s} onClick={() => setInput(s)} className="text-left text-xs text-slate-500 hover:text-blue-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 hover:border-blue-300 rounded-lg px-3 py-2 transition-all duration-150">{s}</button>
              ))}
            </div>
          </div>
        )}
        {isLoadingHistory && <div className="flex items-center justify-center h-full"><Loader2 className="w-5 h-5 text-blue-600 animate-spin" /></div>}
        <div className="px-4 py-4 space-y-5 max-w-3xl mx-auto">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] ${msg.role === "user" ? "bg-blue-50 border border-blue-200 rounded-2xl rounded-br-md" : "bg-slate-50 border border-slate-200 rounded-2xl rounded-bl-md"} px-4 py-3`}>
                {msg.role === "assistant" && (msg.department || msg.agent) && (
                  <div className="mb-2"><RoutingPath department={msg.department ?? null} agent={msg.agent ?? null} compact /></div>
                )}
                {msg.role === "assistant" && isStreaming && i === messages.length - 1 && routingEvents.length > 0 && (
                  <div className="mb-2 flex items-center gap-2 flex-wrap">
                    {routingEvents.map((evt, j) => (
                      <span key={j} className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 border border-blue-200 animate-trace">{evt.label}{evt.detail ? ` → ${evt.detail}` : ""}</span>
                    ))}
                  </div>
                )}
                <div className="text-sm leading-relaxed text-slate-900 prose prose-sm prose-slate max-w-none">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                  {isStreaming && i === messages.length - 1 && msg.role === "assistant" && (
                    <span className="inline-block w-1.5 h-4 bg-blue-600 ml-0.5 animate-pulse align-middle" />
                  )}
                </div>
                {msg.role === "assistant" && msg.model && <p className="text-[10px] text-slate-400 mt-2">via {msg.model}</p>}
              </div>
            </div>
          ))}
          {isStreaming && messages[messages.length - 1]?.content === "" && (
            <div className="flex justify-start">
              <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-2.5 mb-2"><Loader2 className="w-4 h-4 text-blue-600 animate-spin" /><span className="text-xs text-blue-600 font-medium">{routingStage === "classifying" && "Classifying intent…"}{routingStage === "routing" && "Routing to department…"}{routingStage === "processing" && "Agent processing…"}{routingStage === "department" && "Department matched…"}{routingStage === "agent" && "Agent selected…"}{!routingStage && "Working…"}</span></div>
                <div className="w-48 h-1 bg-slate-200 rounded-full overflow-hidden"><div className="h-full bg-gradient-to-r from-blue-700 via-blue-500 to-blue-400 rounded-full animate-load" /></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <form onSubmit={handleSubmit} className="shrink-0 border-t border-slate-200 p-4">
        <div className="max-w-3xl mx-auto space-y-2">
          <div className="flex items-center gap-2">
            <AgentSelector value={targetAgent} onChange={setTargetAgent} />
            {targetAgent && <span className="text-[11px] text-blue-500/70">Sending directly to selected agent — routing bypassed</span>}
            {!wsMode && <span className="text-[11px] text-amber-600">REST mode (WebSocket unavailable)</span>}
          </div>
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {attachments.map((a, i) => (
                <span key={i} className="inline-flex items-center gap-1 text-[11px] bg-blue-50 border border-blue-200 text-blue-700 rounded-md px-2 py-1">
                  {a.filename.endsWith(".pdf") || a.filename.endsWith(".docx") ? <FileText className="w-3 h-3" /> : <Image className="w-3 h-3" />}
                  <span className="max-w-[120px] truncate">{a.filename}</span>
                  <button type="button" onClick={() => removeAttachment(i)} className="hover:text-blue-900"><X className="w-2.5 h-2.5" /></button>
                </span>
              ))}
              {uploading && <span className="text-[11px] text-slate-400 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Uploading…</span>}
            </div>
          )}
          <div className="flex gap-2.5">
            <input ref={fileInputRef} type="file" onChange={handleFilePick} className="hidden" accept="image/*,.pdf,.docx,.txt,.md,.csv,.json" />
            <button type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading} className="shrink-0 p-2.5 rounded-xl border border-slate-300 text-slate-400 hover:text-blue-600 hover:border-blue-400 transition-colors disabled:opacity-40" title="Attach file">
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
            </button>
            <input ref={inputRef} type="text" value={input} onChange={(e) => setInput(e.target.value)}
              placeholder={targetAgent ? "Send a message directly to this agent…" : "Send a message to the orchestration system…"}
              className="flex-1 bg-white border border-slate-300 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-300 transition-all"
              autoFocus disabled={isStreaming || sendMessageMutation.isPending} />
            <button type="submit" disabled={isStreaming || sendMessageMutation.isPending || (!input.trim() && attachments.length === 0)}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:hover:bg-blue-600 text-white rounded-xl px-4 py-2.5 transition-all duration-150 flex items-center gap-2 font-medium text-sm">
              {isStreaming || sendMessageMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </form>

      <style jsx>{`@keyframes load{0%{width:0%}40%{width:40%}70%{width:70%}90%{width:85%}100%{width:90%}}.animate-load{animation:load 3s cubic-bezier(0.16,1,0.3,1) forwards}`}</style>
    </div>
    </>
  );
}
