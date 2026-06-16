"use client";

import { useState } from "react";
import { Bot, Search, ChevronDown } from "lucide-react";
import { useAgents } from "@/lib/hooks";

export default function AgentsSettingsPage() {
  const { data: agents = [], isLoading } = useAgents();
  const [search, setSearch] = useState("");
  const [pinned, setPinned] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState(false);

  const filtered = search.trim()
    ? agents.filter((a) => a.name.toLowerCase().includes(search.toLowerCase()) || a.role.toLowerCase().includes(search.toLowerCase()))
    : agents;

  const togglePin = (role: string) => {
    const next = new Set(pinned);
    if (next.has(role)) next.delete(role); else next.add(role);
    setPinned(next);
  };

  return (
    <div className="max-w-2xl px-8 py-8 space-y-8">
      <div>
        <h2 className="text-base font-semibold text-slate-800 mb-1">Agent Preferences</h2>
        <p className="text-sm text-slate-500">Pin preferred agents and configure routing behavior.</p>
      </div>

      <section className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-800 mb-1">Pinned agents</h3>
          <p className="text-xs text-slate-400 mb-3">Pinned agents are prioritized during routing. Click an agent to pin or unpin it.</p>
          {pinned.size > 0 ? (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {[...pinned].map((role) => (
                <span key={role} className="inline-flex items-center gap-1 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded-md px-2 py-1">
                  <Bot className="w-3 h-3" />
                  {agents.find((a) => a.role === role)?.name || role}
                  <button onClick={() => togglePin(role)} className="hover:text-blue-900 ml-0.5">×</button>
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400 mb-3">No agents pinned. Pinned agents are suggested first during routing.</p>
          )}
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search agents…"
            className="w-full bg-white border border-slate-300 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400"
          />
        </div>

        <div className="space-y-1 max-h-[500px] overflow-y-auto">
          {isLoading && <p className="text-sm text-slate-400 py-4 text-center">Loading agents…</p>}
          {!isLoading && filtered.length === 0 && <p className="text-sm text-slate-400 py-4 text-center">No agents found.</p>}
          {filtered.slice(0, expanded ? undefined : 15).map((agent) => (
            <button
              key={agent.role}
              onClick={() => togglePin(agent.role)}
              className={`w-full text-left flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-sm ${
                pinned.has(agent.role)
                  ? "bg-blue-50 text-blue-700 border border-blue-200"
                  : "text-slate-600 hover:bg-slate-50 border border-transparent"
              }`}
            >
              <div className={`w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                pinned.has(agent.role) ? "bg-blue-600 border-blue-600" : "border-slate-300"
              }`}>
                {pinned.has(agent.role) && <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{agent.name}</div>
                <div className="text-[11px] text-slate-400 font-mono truncate">{agent.role}</div>
              </div>
              <span className="text-[10px] text-slate-400 shrink-0">{agent.tasks.length} tasks</span>
            </button>
          ))}
          {filtered.length > 15 && (
            <button onClick={() => setExpanded(!expanded)} className="w-full text-xs text-blue-600 hover:text-blue-700 py-2 flex items-center justify-center gap-1">
              <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? "rotate-180" : ""}`} />
              {expanded ? "Show fewer" : `Show all ${filtered.length} agents`}
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
