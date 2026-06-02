"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Network, Loader2 } from "lucide-react";
import { sendMessage, type ChatResponse } from "@/lib/api";
import { RoutingPath } from "@/components/routing-path";

interface Message {
  role: "user" | "assistant";
  content: string;
  agent?: string | null;
  department?: string | null;
  model?: string | null;
}

interface ChatInterfaceProps {
  conversationId?: string;
  onConversationChange?: (id: string) => void;
}

export function ChatInterface({ conversationId: initialId, onConversationChange }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(initialId);
  const [routingStage, setRoutingStage] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, routingStage]);

  useEffect(() => {
    if (initialId) {
      setConversationId(initialId);
      setMessages([]);
    }
  }, [initialId]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    // Simulate routing stages for visual feedback
    setRoutingStage("classifying");
    const classifyTimer = setTimeout(() => setRoutingStage("routing"), 600);
    const routeTimer = setTimeout(() => setRoutingStage("processing"), 1200);

    try {
      const response: ChatResponse = await sendMessage(userMessage, conversationId);
      clearTimeout(classifyTimer);
      clearTimeout(routeTimer);
      setRoutingStage("");

      const newId = response.conversation_id;
      if (!conversationId && newId) {
        setConversationId(newId);
        onConversationChange?.(newId);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.response,
          agent: response.agent,
          department: response.routed_to,
          model: response.model,
        },
      ]);
    } catch {
      clearTimeout(classifyTimer);
      clearTimeout(routeTimer);
      setRoutingStage("");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Could not reach the backend. Make sure the server is running on port 8000.",
        },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }, [input, isLoading, conversationId, onConversationChange]);

  const handleNewConversation = useCallback(() => {
    setMessages([]);
    setConversationId(undefined);
    onConversationChange?.("");
  }, [onConversationChange]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="shrink-0 border-b border-warm-800/60 px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse-glow" />
          <span className="text-sm font-medium text-warm-200">
            {conversationId ? "Conversation" : "New Conversation"}
          </span>
        </div>
        {messages.length > 0 && (
          <button
            onClick={handleNewConversation}
            className="text-xs text-warm-400 hover:text-amber-400 transition-colors"
          >
            New chat
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-6">
            <div className="w-16 h-16 rounded-2xl bg-amber-950/30 border border-amber-900/30 flex items-center justify-center mb-5">
              <Network className="w-7 h-7 text-amber-500" />
            </div>
            <h2 className="text-lg font-semibold text-warm-200 mb-2">
              AutoSteer
            </h2>
            <p className="text-sm text-warm-400 max-w-md">
              Send a message and watch it route through the Master Orchestrator to the
              most qualified agent across 12 departments and 42 specialists.
            </p>
            <div className="mt-6 grid grid-cols-2 gap-2 w-full max-w-sm">
              {[
                "Research the latest transformer architectures",
                "Design a new onboarding flow for enterprise customers",
                "Draft a sales proposal for Acme Corp",
                "Review my API for security vulnerabilities",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => setInput(suggestion)}
                  className="text-left text-xs text-warm-400 hover:text-amber-300 bg-warm-800/40 hover:bg-warm-800/70 border border-warm-700/40 hover:border-amber-800/50 rounded-lg px-3 py-2 transition-all duration-150"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="px-4 py-4 space-y-5 max-w-3xl mx-auto">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] ${
                  msg.role === "user"
                    ? "bg-amber-950/30 border border-amber-900/40 rounded-2xl rounded-br-md"
                    : "bg-warm-800/40 border border-warm-700/50 rounded-2xl rounded-bl-md"
                } px-4 py-3`}
              >
                {/* Routing path for assistant messages */}
                {msg.role === "assistant" && (msg.department || msg.agent) && (
                  <div className="mb-2">
                    <RoutingPath
                      department={msg.department ?? null}
                      agent={msg.agent ?? null}
                      compact
                    />
                  </div>
                )}

                <p className="text-sm leading-relaxed whitespace-pre-wrap text-warm-100">
                  {msg.content}
                </p>

                {msg.role === "assistant" && msg.model && (
                  <p className="text-[10px] text-warm-600 mt-2">
                    via {msg.model}
                  </p>
                )}
              </div>
            </div>
          ))}

          {/* Loading indicator with routing stage */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-warm-800/40 border border-warm-700/50 rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-2.5 mb-2">
                  <Loader2 className="w-4 h-4 text-amber-500 animate-spin" />
                  <span className="text-xs text-amber-400 font-medium">
                    {routingStage === "classifying" && "Classifying intent…"}
                    {routingStage === "routing" && "Routing to department…"}
                    {routingStage === "processing" && "Agent processing…"}
                    {!routingStage && "Working…"}
                  </span>
                </div>
                <div className="w-48 h-1 bg-warm-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-amber-800 via-amber-500 to-amber-400 rounded-full animate-load"
                  />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="shrink-0 border-t border-warm-800/60 p-4"
      >
        <div className="max-w-3xl mx-auto flex gap-2.5">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Send a message to the orchestration system…"
            className="flex-1 bg-warm-800/60 border border-warm-700/60 rounded-xl px-4 py-2.5 text-sm text-warm-100 placeholder-warm-500 focus:outline-none focus:border-amber-700/70 focus:ring-1 focus:ring-amber-800/50 transition-all"
            autoFocus
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-amber-600 hover:bg-amber-500 disabled:opacity-40 disabled:hover:bg-amber-600 text-warm-950 rounded-xl px-4 py-2.5 transition-all duration-150 flex items-center gap-2 font-medium text-sm"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>

      <style jsx>{`
        @keyframes load {
          0% {
            width: 0%;
          }
          40% {
            width: 40%;
          }
          70% {
            width: 70%;
          }
          90% {
            width: 85%;
          }
          100% {
            width: 90%;
          }
        }
        .animate-load {
          animation: load 3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
      `}</style>
    </div>
  );
}
