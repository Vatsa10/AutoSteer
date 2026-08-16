import { create } from "zustand";

// ── Toast notifications ──────────────────────────────────────────

export interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

interface ToastStore {
  toasts: Toast[];
  addToast: (message: string, type?: Toast["type"]) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (message, type = "info") => {
    const id = Math.random().toString(36).slice(2, 9);
    set((s) => ({ toasts: [...s.toasts, { id, message, type }] }));
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
    }, 5000);
  },
  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

// ── Chat state ───────────────────────────────────────────────────

export interface ToolTrace { name: string; status: string; result_summary: string; duration_ms: number }
export interface SourceTrace { filename: string; chunk_index: number; score: number; snippet: string }
export interface StepTrace { id: string; status: string; label: string }
export interface ArtifactRef { id: string; title: string; kind: string; filename: string | null }

export interface AgentNode {
  id: string;
  agent: string;
  department: string;
  description: string;
  content?: string;
  status: "running" | "ok" | "error";
  elapsed_ms?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string | null;
  department?: string | null;
  model?: string | null;
  tools?: ToolTrace[];
  sources?: SourceTrace[];
  steps?: StepTrace[];
  artifacts?: ArtifactRef[];
  agentNodes?: AgentNode[];
}

export type RoutingStage = "classifying" | "routing" | "department" | "agent" | "processing" | "";

interface ChatStore {
  messages: ChatMessage[];
  conversationId: string | undefined;
  targetAgent: string | null;
  routingStage: RoutingStage;
  routingEvents: RoutingEvent[];
  isStreaming: boolean;

  setMessages: (messages: ChatMessage[]) => void;
  addMessage: (message: Omit<ChatMessage, "id"> & { id?: string }) => string;
  appendContent: (content: string) => void;
  replaceLastContent: (content: string) => void;
  updateLastMeta: (meta: Pick<ChatMessage, "agent" | "department" | "model">) => void;
  dropLastIfEmptyAssistant: () => void;
  setConversationId: (id: string | undefined) => void;
  setTargetAgent: (agent: string | null) => void;
  setRoutingStage: (stage: RoutingStage) => void;
  addRoutingEvent: (event: RoutingEvent) => void;
  clearRoutingEvents: () => void;
  setIsStreaming: (v: boolean) => void;
  reset: () => void;
  addToolTrace: (t: ToolTrace) => void;
  addSourceTrace: (s: SourceTrace) => void;
  addStepTrace: (s: StepTrace) => void;
  addArtifactRef: (a: ArtifactRef) => void;
  startAgentNode: (n: AgentNode) => void;
  endAgentNode: (id: string, content: string, status: "ok" | "error", elapsed_ms: number) => void;
  settleAgentNodes: () => void;
}

export interface RoutingEvent {
  type: "classifying" | "department" | "agent" | "processing" | "done";
  label: string;
  detail?: string;
}

const initialChatState = {
  messages: [] as ChatMessage[],
  conversationId: undefined as string | undefined,
  targetAgent: null as string | null,
  routingStage: "" as RoutingStage,
  routingEvents: [] as RoutingEvent[],
  isStreaming: false,
};

export const useChatStore = create<ChatStore>((set) => ({
  ...initialChatState,

  setMessages: (messages) => set({ messages }),
  addMessage: (message) => {
    const id = message.id ?? `m-${Math.random().toString(36).slice(2, 10)}`;
    set((s) => ({ messages: [...s.messages, { ...message, id }] }));
    return id;
  },
  appendContent: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + content };
      }
      return { messages: msgs };
    }),
  replaceLastContent: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content };
      }
      return { messages: msgs };
    }),
  updateLastMeta: (meta) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = {
          ...last,
          agent: meta.agent ?? last.agent,
          department: meta.department ?? last.department,
          model: meta.model ?? last.model,
        };
      }
      return { messages: msgs };
    }),
  dropLastIfEmptyAssistant: () =>
    set((s) => {
      const last = s.messages[s.messages.length - 1];
      if (last && last.role === "assistant" && last.content === "") {
        return { messages: s.messages.slice(0, -1) };
      }
      return {};
    }),
  addToolTrace: (t) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, tools: [...(last.tools || []), t] };
      }
      return { messages: msgs };
    }),
  addSourceTrace: (src) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, sources: [...(last.sources || []), src] };
      }
      return { messages: msgs };
    }),
  addStepTrace: (st) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        const steps = [...(last.steps || [])];
        const i = steps.findIndex((x) => x.id === st.id);
        if (i >= 0) steps[i] = st; else steps.push(st);  // update status in place
        msgs[msgs.length - 1] = { ...last, steps };
      }
      return { messages: msgs };
    }),
  addArtifactRef: (a) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, artifacts: [...(last.artifacts || []), a] };
      }
      return { messages: msgs };
    }),
  startAgentNode: (n) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, agentNodes: [...(last.agentNodes || []), n] };
      }
      return { messages: msgs };
    }),
  endAgentNode: (id, content, status, elapsed_ms) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        const nodes = (last.agentNodes || []).map((n) =>
          n.id === id ? { ...n, content, status, elapsed_ms } : n);
        msgs[msgs.length - 1] = { ...last, agentNodes: nodes };
      }
      return { messages: msgs };
    }),
  settleAgentNodes: () =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant" && last.agentNodes) {
        const nodes = last.agentNodes.map((n) =>
          n.status === "running" ? { ...n, status: "ok" as const } : n);
        msgs[msgs.length - 1] = { ...last, agentNodes: nodes };
      }
      return { messages: msgs };
    }),
  setConversationId: (id) => set({ conversationId: id }),
  setTargetAgent: (agent) => set({ targetAgent: agent }),
  setRoutingStage: (stage) => set({ routingStage: stage }),
  addRoutingEvent: (event) =>
    set((s) => ({ routingEvents: [...s.routingEvents, event] })),
  clearRoutingEvents: () => set({ routingEvents: [] }),
  setIsStreaming: (v) => set({ isStreaming: v }),
  reset: () =>
    set({
      messages: [],
      conversationId: undefined,
      targetAgent: null,
      routingStage: "",
      routingEvents: [],
      isStreaming: false,
    }),
}));
