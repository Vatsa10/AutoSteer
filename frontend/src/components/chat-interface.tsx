"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Network, Loader2 } from "lucide-react";
import { sendMessage, type ChatResponse } from "@/lib/api";
import { RoutingPath } from "@/components/routing-path";
import { AgentSelector } from "@/components/agent-selector";

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
  const [targetAgent, setTargetAgent] = useState<string | null>(null);
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    const agent = targetAgent;
    const convId = conversationId;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    // Simulate routing stages for visual feedback (skip for direct agent)
    if (agent) {
      setRoutingStage("processing");
    } else {
      setRoutingStage("classifying");
    }
    const classifyTimer = setTimeout(() => setRoutingStage("routing"), 600);
    const routeTimer = setTimeout(() => setRoutingStage("processing"), 1200);

    try {
      const response: ChatResponse = await sendMessage(
        userMessage,
        convId,
        agent ?? undefined,
      );
      clearTimeout(classifyTimer);
      clearTimeout(routeTimer);
      setRoutingStage("");

      if (!convId && response.conversation_id) {
        setConversationId(response.conversation_id);
        onConversationChange?.(response.conversation_id);
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
  }

  function handleNewConversation() {
    setMessages([]);
    setConversationId(undefined);
    onConversationChange?.("");
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="shrink-0 border-b border-slate-200 px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-blue-600 animate-pulse-glow" />
          <span className="text-sm font-medium text-slate-800">
            {conversationId ? "Conversation" : "New Conversation"}
          </span>
        </div>
        {messages.length > 0 && (
          <button
            onClick={handleNewConversation}
            className="text-xs text-slate-500 hover:text-blue-600 transition-colors"
          >
            New chat
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-6">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center mb-5">
              <Network className="w-7 h-7 text-blue-600" />
            </div>
            <h2 className="text-lg font-semibold text-slate-800 mb-2">
              AutoSteer
            </h2>
            <p className="text-sm text-slate-500 max-w-md">
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
                  className="text-left text-xs text-slate-500 hover:text-blue-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 hover:border-blue-300 rounded-lg px-3 py-2 transition-all duration-150"
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
                    ? "bg-blue-50 border border-blue-200 rounded-2xl rounded-br-md"
                    : "bg-slate-50 border border-slate-200 rounded-2xl rounded-bl-md"
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

                <p className="text-sm leading-relaxed whitespace-pre-wrap text-slate-900">
                  {msg.content}
                </p>

                {msg.role === "assistant" && msg.model && (
                  <p className="text-[10px] text-slate-400 mt-2">
                    via {msg.model}
                  </p>
                )}
              </div>
            </div>
          ))}

          {/* Loading indicator with routing stage */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-2.5 mb-2">
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                  <span className="text-xs text-blue-600 font-medium">
                    {routingStage === "classifying" && "Classifying intent…"}
                    {routingStage === "routing" && "Routing to department…"}
                    {routingStage === "processing" && "Agent processing…"}
                    {!routingStage && "Working…"}
                  </span>
                </div>
                <div className="w-48 h-1 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-700 via-blue-500 to-blue-400 rounded-full animate-load"
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
        className="shrink-0 border-t border-slate-200 p-4"
      >
        <div className="max-w-3xl mx-auto space-y-2">
          <div className="flex items-center gap-2">
            <AgentSelector value={targetAgent} onChange={setTargetAgent} />
            {targetAgent && (
              <span className="text-[11px] text-blue-500/70">
                Sending directly to selected agent — routing bypassed
              </span>
            )}
          </div>
          <div className="flex gap-2.5">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                targetAgent
                  ? `Send a message directly to this agent…`
                  : "Send a message to the orchestration system…"
              }
              className="flex-1 bg-white border border-slate-300 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-300 transition-all"
              autoFocus
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:hover:bg-blue-600 text-white rounded-xl px-4 py-2.5 transition-all duration-150 flex items-center gap-2 font-medium text-sm"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
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
