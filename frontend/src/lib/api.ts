const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}

// Agents
export async function getAgents(): Promise<AgentInfo[]> {
  const res = await fetch(`${API_URL}/api/agents`);
  if (!res.ok) throw new Error(`Failed to fetch agents: ${res.status}`);
  return res.json();
}

export async function getDepartments(): Promise<DepartmentInfo[]> {
  const res = await fetch(`${API_URL}/api/departments`);
  if (!res.ok) throw new Error(`Failed to fetch departments: ${res.status}`);
  return res.json();
}

// Conversations
export async function getConversations(): Promise<Conversation[]> {
  const res = await fetch(`${API_URL}/api/conversations`);
  if (!res.ok) throw new Error(`Failed to fetch conversations: ${res.status}`);
  return res.json();
}

export async function getConversationMessages(
  conversationId: string,
): Promise<ConversationMessage[]> {
  const res = await fetch(`${API_URL}/api/conversations/${conversationId}/messages`);
  if (!res.ok) throw new Error(`Failed to fetch messages: ${res.status}`);
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
  const res = await fetch(`${API_URL}/api/status`);
  if (!res.ok) throw new Error(`Failed to fetch status: ${res.status}`);
  return res.json();
}
