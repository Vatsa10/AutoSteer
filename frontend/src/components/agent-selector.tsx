"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Bot, Network, X, ChevronDown } from "lucide-react";
import { getAgents, type AgentInfo } from "@/lib/api";

interface AgentSelectorProps {
  value: string | null;
  onChange: (agentRole: string | null) => void;
}

const deptColors: Record<string, string> = {
  engineering: "text-blue-600",
  data_analytics: "text-teal-600",
  product: "text-violet-600",
  design: "text-pink-600",
  sales: "text-green-600",
  marketing: "text-orange-600",
  customer_success: "text-cyan-600",
  trust_safety: "text-red-600",
  operations: "text-yellow-600",
  people_talent: "text-purple-600",
  finance_legal: "text-emerald-600",
  executive: "text-amber-600",
};

const deptLabels: Record<string, string> = {
  engineering: "Engineering",
  data_analytics: "Data & Analytics",
  product: "Product",
  design: "Design",
  sales: "Sales",
  marketing: "Marketing",
  customer_success: "Customer Success",
  trust_safety: "Trust & Safety",
  operations: "Operations",
  people_talent: "People & Talent",
  finance_legal: "Finance & Legal",
  executive: "Executive",
};

function formatDept(key: string): string {
  return deptLabels[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function AgentSelector({ value, onChange }: AgentSelectorProps) {
  const [open, setOpen] = useState(false);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getAgents()
      .then(setAgents)
      .catch(() => {});
  }, []);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const selectedAgent = value ? agents.find((a) => a.role === value) : null;

  const filtered = search.trim()
    ? agents.filter(
        (a) =>
          a.name.toLowerCase().includes(search.toLowerCase()) ||
          a.role.toLowerCase().includes(search.toLowerCase()) ||
          a.department.toLowerCase().includes(search.toLowerCase()),
      )
    : agents;

  // Group by department
  const grouped = new Map<string, AgentInfo[]>();
  for (const a of filtered) {
    const existing = grouped.get(a.department) ?? [];
    existing.push(a);
    grouped.set(a.department, existing);
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 text-xs rounded-lg px-2.5 py-1.5 border transition-all ${
          selectedAgent
            ? "bg-blue-50 border-blue-200 text-blue-700"
            : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700 hover:border-slate-300"
        }`}
      >
        {selectedAgent ? (
          <>
            <Bot className="w-3 h-3" />
            <span className="max-w-[120px] truncate">{selectedAgent.name}</span>
          </>
        ) : (
          <>
            <Network className="w-3 h-3" />
            <span>Auto</span>
          </>
        )}
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {selectedAgent && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onChange(null);
          }}
          className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-slate-300 border border-slate-400 flex items-center justify-center text-white hover:bg-slate-500 transition-colors"
        >
          <X className="w-2.5 h-2.5" />
        </button>
      )}

      {open && (
        <div className="absolute bottom-full mb-1 left-0 w-72 bg-white border border-slate-200 rounded-xl shadow-xl z-50 overflow-hidden">
          <div className="p-2 border-b border-slate-200">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search agents…"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400"
                autoFocus
              />
            </div>
          </div>

          <div className="max-h-64 overflow-y-auto">
            {/* Auto option */}
            <button
              type="button"
              onClick={() => {
                onChange(null);
                setOpen(false);
                setSearch("");
              }}
              className={`w-full text-left px-3 py-2 text-xs flex items-center gap-2.5 hover:bg-slate-50 transition-colors ${
                !value ? "bg-blue-50 text-blue-700" : "text-slate-700"
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              <div>
                <div className="font-medium">Auto (let system route)</div>
                <div className="text-[10px] text-slate-500">
                  Master Orchestrator picks the best agent
                </div>
              </div>
            </button>

            {Array.from(grouped.entries()).map(([dept, deptAgents]) => (
              <div key={dept}>
                <div className="px-3 py-1.5 text-[10px] font-medium text-slate-500 uppercase tracking-wider border-t border-slate-100">
                  {formatDept(dept)}
                </div>
                {deptAgents.map((agent) => (
                  <button
                    key={agent.role}
                    type="button"
                    onClick={() => {
                      onChange(agent.role);
                      setOpen(false);
                      setSearch("");
                    }}
                    className={`w-full text-left px-3 py-1.5 text-xs flex items-center gap-2.5 hover:bg-slate-50 transition-colors ${
                      value === agent.role
                        ? "bg-blue-50 text-blue-700"
                        : "text-slate-700"
                    }`}
                  >
                    <Bot className={`w-3.5 h-3.5 ${deptColors[dept] ?? "text-slate-400"}`} />
                    <div className="min-w-0">
                      <div className="font-medium truncate">{agent.name}</div>
                      <div className="text-[10px] text-slate-500 truncate">{agent.role}</div>
                    </div>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
