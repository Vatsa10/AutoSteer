"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Bot, Network, X, ChevronDown } from "lucide-react";
import { getAgents, type AgentInfo } from "@/lib/api";

interface AgentSelectorProps {
  value: string | null;
  onChange: (agentRole: string | null) => void;
}

const deptColors: Record<string, string> = {
  engineering: "text-blue-400",
  data_analytics: "text-teal-400",
  product: "text-violet-400",
  design: "text-pink-400",
  sales: "text-green-400",
  marketing: "text-orange-400",
  customer_success: "text-cyan-400",
  trust_safety: "text-red-400",
  operations: "text-yellow-400",
  people_talent: "text-purple-400",
  finance_legal: "text-emerald-400",
  executive: "text-amber-400",
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
            ? "bg-amber-950/30 border-amber-800/50 text-amber-300"
            : "bg-warm-800/60 border-warm-700/60 text-warm-400 hover:text-warm-300 hover:border-warm-600"
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
          className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-warm-600 border border-warm-500 flex items-center justify-center text-warm-300 hover:bg-warm-500 transition-colors"
        >
          <X className="w-2.5 h-2.5" />
        </button>
      )}

      {open && (
        <div className="absolute bottom-full mb-1 left-0 w-72 bg-warm-900 border border-warm-700 rounded-xl shadow-xl z-50 overflow-hidden">
          <div className="p-2 border-b border-warm-800">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-warm-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search agents…"
                className="w-full bg-warm-800/60 border border-warm-700/60 rounded-lg pl-8 pr-3 py-1.5 text-xs text-warm-100 placeholder-warm-500 focus:outline-none focus:border-amber-700/70"
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
              className={`w-full text-left px-3 py-2 text-xs flex items-center gap-2.5 hover:bg-warm-800/40 transition-colors ${
                !value ? "bg-amber-950/20 text-amber-300" : "text-warm-300"
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              <div>
                <div className="font-medium">Auto (let system route)</div>
                <div className="text-[10px] text-warm-500">
                  Master Orchestrator picks the best agent
                </div>
              </div>
            </button>

            {Array.from(grouped.entries()).map(([dept, deptAgents]) => (
              <div key={dept}>
                <div className="px-3 py-1.5 text-[10px] font-medium text-warm-500 uppercase tracking-wider border-t border-warm-800/60">
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
                    className={`w-full text-left px-3 py-1.5 text-xs flex items-center gap-2.5 hover:bg-warm-800/40 transition-colors ${
                      value === agent.role
                        ? "bg-amber-950/20 text-amber-300"
                        : "text-warm-300"
                    }`}
                  >
                    <Bot className={`w-3.5 h-3.5 ${deptColors[dept] ?? "text-warm-400"}`} />
                    <div className="min-w-0">
                      <div className="font-medium truncate">{agent.name}</div>
                      <div className="text-[10px] text-warm-500 truncate">{agent.role}</div>
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
