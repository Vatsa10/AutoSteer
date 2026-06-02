"use client";

import { useState } from "react";
import { Loader2, Plus } from "lucide-react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

export default function CustomAgentsPage() {
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [department, setDepartment] = useState("product");
  const [identity, setIdentity] = useState("");
  const [tools, setTools] = useState("web_search, notion_export");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (API_KEY) headers["X-API-Key"] = API_KEY;
      const res = await fetch(`${API_URL}/api/custom-agents`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          name,
          role,
          department,
          identity,
          tools: tools.split(",").map((t) => t.trim()).filter(Boolean),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      setMessage(`Created agent "${data.role}". Restart backend to load into routing.`);
      setName("");
      setRole("");
      setIdentity("");
    } catch (err) {
      setMessage(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Custom Agent</h1>
          <p className="text-sm text-slate-500">Create a DB-backed agent with tool allowlist.</p>
        </div>
        <Link href="/agents" className="text-sm text-blue-600 hover:underline">
          Browse agents
        </Link>
      </div>

      <form onSubmit={handleCreate} className="space-y-4 border border-slate-200 rounded-xl p-4">
        <input
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
          placeholder="Display name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
          placeholder="Role slug (e.g. my_analyst)"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          required
        />
        <select
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
        >
          {["product", "engineering", "sales", "marketing", "operations", "customer_success"].map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <textarea
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm min-h-[80px]"
          placeholder="Agent identity / soul"
          value={identity}
          onChange={(e) => setIdentity(e.target.value)}
          required
        />
        <input
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono text-xs"
          placeholder="Tools (comma-separated canonical names)"
          value={tools}
          onChange={(e) => setTools(e.target.value)}
        />
        <button
          type="submit"
          disabled={busy}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg bg-blue-600 text-white disabled:opacity-50"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Create agent
        </button>
      </form>

      {message && (
        <p className="mt-4 text-sm text-slate-600 border border-slate-100 rounded-lg p-3 bg-slate-50">{message}</p>
      )}
    </div>
  );
}
