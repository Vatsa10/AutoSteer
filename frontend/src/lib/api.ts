const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  return headers;
}

async function apiFetch(path: string, options?: RequestInit): Promise<Response> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...authHeaders(),
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`API error (${res.status}): ${errText}`);
  }
  return res;
}

export interface ChatResponse {
  conversation_id: string;
  response: string;
  routed_to: string | null;
  agent: string | null;
  model: string | null;
  usage: Record<string, number> | null;
}

export interface AgentInfo {
  role: string;
  name: string;
  department: string;
  tasks: string[];
}

export interface DepartmentInfo {
  name: string;
  department: string;
  agents: string[];
}

export interface Conversation {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  from_agent: string;
  to_agent: string;
  message_type: "request" | "response" | "escalation" | "notification" | "handoff";
  priority: "P0" | "P1" | "P2" | "P3" | "P4";
  content: string;
  thread_id: string;
  created_at: string;
}

// Chat
export async function sendMessage(
  message: string,
  conversationId?: string,
  targetAgent?: string,
): Promise<ChatResponse> {
  const res = await apiFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      target_agent: targetAgent || null,
    }),
  });
  return res.json();
}

// Agents
export async function getAgents(): Promise<AgentInfo[]> {
  const res = await apiFetch("/api/agents");
  return res.json();
}

export async function getDepartments(): Promise<DepartmentInfo[]> {
  const res = await apiFetch("/api/departments");
  return res.json();
}

// Conversations
export async function getConversations(): Promise<Conversation[]> {
  const res = await apiFetch("/api/conversations");
  return res.json();
}

export async function getConversationMessages(
  conversationId: string,
): Promise<ConversationMessage[]> {
  const res = await apiFetch(`/api/conversations/${conversationId}/messages`);
  return res.json();
}

// Status
export interface SystemStatus {
  total_agents: number;
  total_departments: number;
  llm_provider: string;
  uptime_seconds: number;
}

export async function getSystemStatus(): Promise<SystemStatus> {
  const res = await apiFetch("/api/status");
  return res.json();
}
