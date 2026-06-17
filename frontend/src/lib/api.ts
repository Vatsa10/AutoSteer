const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

export async function authHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  // Send Clerk session token for auth
  try {
    const token = await (window as any).Clerk?.session?.getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  } catch {}
  return headers;
}

async function apiFetch(path: string, options?: RequestInit): Promise<Response> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { ...headers, ...(options?.headers || {}) },
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
  structured?: {
    sections: { type: string; title: string; items: string[] }[];
  } | null;
}

// File upload
export interface FileUploadResult {
  ok: boolean;
  file_id: string;
  filename: string;
  size_bytes: number;
}

export async function uploadFile(file: File): Promise<FileUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_URL}/api/files/upload`, {
    method: "POST",
    headers: API_KEY ? { "X-API-Key": API_KEY } : {},
    body: formData,
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Upload failed (${res.status}): ${errText}`);
  }
  return res.json();
}

export interface AgentToolStatus {
  yaml_name: string;
  canonical: string;
  tier: string;
  status: "live" | "beta" | "planned";
  callable: boolean;
}

export interface AgentInfo {
  role: string;
  name: string;
  department: string;
  tasks: string[];
  tools?: AgentToolStatus[];
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

export async function deleteConversation(conversationId: string): Promise<void> {
  await apiFetch(`/api/conversations/${conversationId}`, { method: "DELETE" });
}

// Preferences
export async function getPreferences(): Promise<{ about: string; responseStyle: string; defaultAgent: string }> {
  const res = await apiFetch("/api/preferences");
  return res.json();
}

export async function savePreferences(prefs: { about: string; responseStyle: string; defaultAgent: string }): Promise<void> {
  await apiFetch("/api/preferences", { method: "PUT", body: JSON.stringify(prefs) });
}

// Memory
export async function getMemory(): Promise<{ facts: { id: string; fact_type: string; key: string; value: string }[]; documents: { filename: string; preview: string; char_count: number }[]; summary: string }> {
  const res = await apiFetch("/api/memory");
  return res.json();
}

export async function addMemoryFact(fact: { fact_type: string; key: string; value: string }): Promise<{ ok: boolean; id: string }> {
  const res = await apiFetch("/api/memory/facts", { method: "POST", body: JSON.stringify(fact) });
  return res.json();
}

export async function deleteMemoryFact(id: string): Promise<void> {
  await apiFetch(`/api/memory/facts/${id}`, { method: "DELETE" });
}

export async function saveMemoryDocuments(data: { documents: unknown[]; summary: string }): Promise<void> {
  await apiFetch("/api/memory/documents", { method: "PUT", body: JSON.stringify(data) });
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

// Integrations
export interface IntegrationProvider {
  id: string;
  name: string;
  description: string;
  scopes: string[];
  connect_type: string;
  env_var: string;
  connected: boolean;
  connection_source: string | null;
}

export async function getIntegrations(): Promise<{
  providers: IntegrationProvider[];
  workspace_id: string;
}> {
  const res = await apiFetch("/api/integrations");
  return res.json();
}

export async function connectIntegration(
  provider: string,
  token: string,
  metadata?: Record<string, string>,
): Promise<{ ok: boolean }> {
  const res = await apiFetch(`/api/integrations/${provider}/connect`, {
    method: "POST",
    body: JSON.stringify({ token, metadata }),
  });
  return res.json();
}

export async function testIntegration(
  provider: string,
): Promise<{ ok: boolean; error?: string; message?: string }> {
  const res = await apiFetch(`/api/integrations/${provider}/test`, { method: "POST" });
  return res.json();
}

export async function disconnectIntegration(provider: string): Promise<{ ok: boolean }> {
  const res = await apiFetch(`/api/integrations/${provider}/disconnect`, { method: "DELETE" });
  return res.json();
}

export interface ToolInfo {
  name: string;
  description: string;
  tier: string;
  status: string;
  provider: string | null;
}

export async function getTools(): Promise<{ tools: ToolInfo[]; count: number }> {
  const res = await apiFetch("/api/tools");
  return res.json();
}

export interface PricingPlan {
  id: string;
  name: string;
  price_usd: number;
  interval: string;
  features: string[];
  checkout_url: string | null;
}

export async function getPricing(): Promise<{ plans: PricingPlan[]; self_host: { price_usd: number } }> {
  const res = await apiFetch("/api/billing/pricing");
  return res.json();
}
