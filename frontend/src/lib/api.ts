const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

export async function authHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  // Use our own auth token (DB-based sign-in, not Clerk)
  try {
    const token = localStorage.getItem("autosteer_token");
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
  const headers: Record<string, string> = {};
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  try {
    const token = localStorage.getItem("autosteer_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  } catch {}
  const res = await fetch(`${API_URL}/api/files/upload`, {
    method: "POST",
    headers,
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
  last_message?: string | null;
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
export interface MemoryDoc { filename: string; preview: string; char_count: number; pages?: number; vectorized?: boolean; chunks?: number }

export async function getMemory(): Promise<{ facts: { id: string; fact_type: string; key: string; value: string }[]; documents: MemoryDoc[]; summary: string }> {
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

export async function deleteMemoryDocument(index: number): Promise<void> {
  await apiFetch(`/api/memory/documents/${index}`, { method: "DELETE" });
}

export async function uploadMemoryDocument(file: File): Promise<{ ok: boolean; document: MemoryDoc }> {
  const formData = new FormData();
  formData.append("file", file);
  const headers: Record<string, string> = {};
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  try {
    const token = localStorage.getItem("autosteer_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  } catch {}
  const res = await fetch(`${API_URL}/api/memory/documents/upload`, { method: "POST", headers, body: formData });
  if (!res.ok) throw new Error(`Upload failed (${res.status}): ${await res.text()}`);
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

// ── Workflows ─────────────────────────────────────────────────────

export interface WorkflowStepDef {
  id: string;
  type?: string;
  agent?: string | null;
  tool?: string | null;
  description?: string;
  dependencies?: string[];
  config?: Record<string, any>;
}

export interface WorkflowDefinition {
  name: string;
  description: string;
  step_count?: number;
  steps?: WorkflowStepDef[];
}

export interface WorkflowRunStep {
  step_id: string;
  agent: string;
  status: "pending" | "running" | "completed" | "failed";
  output?: string;
  started_at?: string;
  completed_at?: string;
}

export interface WorkflowRun {
  id: string;
  workflow_name: string;
  status: "completed" | "failed" | "running";
  started_at: string;
  completed_at?: string;
  steps: WorkflowRunStep[];
}

export async function getWorkflows(): Promise<WorkflowDefinition[]> {
  const res = await apiFetch("/api/workflows");
  const data = await res.json();
  return data.workflows ?? [];
}

export async function getWorkflow(name: string): Promise<WorkflowDefinition> {
  const res = await apiFetch(`/api/workflows/${encodeURIComponent(name)}`);
  return res.json();
}

export async function getWorkflowRuns(name: string): Promise<{ runs: WorkflowRun[] }> {
  const res = await apiFetch(`/api/workflows/${encodeURIComponent(name)}/runs`);
  return res.json();
}

// ── Approvals ─────────────────────────────────────────────────────

export interface PendingApproval {
  id: string;
  run_id: string;
  step_id: string;
  prompt: string;
  context: string;
  created_at: string;
  status: "pending" | "approved" | "rejected";
}

export async function getPendingApprovals(): Promise<PendingApproval[]> {
  const res = await apiFetch("/api/approvals/pending");
  const data = await res.json();
  return data.pending ?? [];
}

export async function resolveApproval(
  id: string,
  resolution: { action: "approved" | "rejected"; note?: string },
): Promise<void> {
  await apiFetch(`/api/approvals/${encodeURIComponent(id)}/resolve`, {
    method: "POST",
    body: JSON.stringify(resolution),
  });
}

// ── Artifacts ─────────────────────────────────────────────────────

export interface ArtifactSummary {
  id: string; title: string; kind: string; status: string;
  version: number; filename: string | null; conversation_id: string | null; created_at: string | null;
}

export async function getArtifacts(): Promise<{ artifacts: ArtifactSummary[] }> {
  const res = await apiFetch("/api/artifacts");
  return res.json();
}

export async function getArtifact(id: string): Promise<{
  artifact: { id: string; title: string; kind: string; status: string; content: string; filename: string | null; version: number; created_at: string | null };
  versions: { id: string; version: number; status: string; created_at: string | null }[];
}> {
  const res = await apiFetch(`/api/artifacts/${id}`);
  return res.json();
}

export async function approveArtifact(id: string): Promise<void> {
  await apiFetch(`/api/artifacts/${id}/approve`, { method: "POST" });
}

export async function rejectArtifact(id: string): Promise<void> {
  await apiFetch(`/api/artifacts/${id}/reject`, { method: "POST" });
}
