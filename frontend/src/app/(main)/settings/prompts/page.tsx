"use client";

import { useState } from "react";
import { Loader2, Plus, Play, Save } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

async function apiFetch(path: string, options?: RequestInit) {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  const res = await fetch(`${API_URL}${path}`, { ...options, headers: { ...headers, ...options?.headers } });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function PromptsSettingsPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [runOutput, setRunOutput] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["prompts"],
    queryFn: () => apiFetch("/api/prompts"),
  });

  async function handleSave() {
    setBusy(true);
    try {
      await apiFetch("/api/prompts", {
        method: "POST",
        body: JSON.stringify({ name, prompt }),
      });
      setName("");
      setPrompt("");
      queryClient.invalidateQueries({ queryKey: ["prompts"] });
    } finally {
      setBusy(false);
    }
  }

  async function handleRun() {
    setBusy(true);
    setRunOutput(null);
    try {
      const result = await apiFetch("/api/prompts/run", {
        method: "POST",
        body: JSON.stringify({ name: name || undefined, prompt: prompt || undefined }),
      });
      setRunOutput(result.output || JSON.stringify(result, null, 2));
    } catch (e) {
      setRunOutput(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-xl font-semibold text-slate-900 mb-1">Prompt Playground</h1>
      <p className="text-sm text-slate-500 mb-6">Save and run prompts against your default LLM.</p>

      <div className="space-y-4 border border-slate-200 rounded-xl p-4">
        <input
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
          placeholder="Prompt name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <textarea
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm min-h-[120px]"
          placeholder="Prompt text..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={busy || !name || !prompt}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg bg-slate-900 text-white disabled:opacity-50"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save
          </button>
          <button
            onClick={handleRun}
            disabled={busy || !prompt}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg border border-slate-200 disabled:opacity-50"
          >
            <Play className="w-4 h-4" /> Run
          </button>
        </div>
      </div>

      {runOutput && (
        <div className="mt-4 border border-slate-200 rounded-xl p-4 bg-slate-50">
          <h2 className="text-sm font-medium text-slate-700 mb-2">Output</h2>
          <pre className="text-xs text-slate-600 whitespace-pre-wrap">{runOutput}</pre>
        </div>
      )}

      <div className="mt-8">
        <h2 className="text-sm font-medium text-slate-700 mb-3">Saved prompts</h2>
        {isLoading ? (
          <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
        ) : (
          <ul className="space-y-2">
            {(data?.prompts || []).map((p: { name: string; model: string }) => (
              <li
                key={p.name}
                className="flex items-center justify-between text-sm border border-slate-100 rounded-lg px-3 py-2"
              >
                <span className="font-medium">{p.name}</span>
                <span className="text-xs text-slate-400">{p.model}</span>
              </li>
            ))}
            {!data?.prompts?.length && (
              <li className="text-sm text-slate-400 flex items-center gap-1">
                <Plus className="w-4 h-4" /> No saved prompts yet
              </li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
