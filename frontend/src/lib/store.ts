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

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  agent?: string | null;
  department?: string | null;
  model?: string | null;
  tools?: ToolTrace[];
  sources?: SourceTrace[];
  steps?: StepTrace[];
  artifacts?: ArtifactRef[];
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
  addMessage: (message: ChatMessage) => void;
  appendContent: (content: string) => void;
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
  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),
  appendContent: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + content };
      }
      return { messages: msgs };
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
