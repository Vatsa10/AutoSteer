"use client";

import { useState } from "react";
import { ChevronDown, Building2 } from "lucide-react";
import type { AgentInfo } from "@/lib/api";
import { AgentCard } from "@/components/agent-card";

interface DepartmentGroupProps {
  department: string;
  label: string;
  agents: AgentInfo[];
  onSelectAgent: (agent: AgentInfo) => void;
}

export function DepartmentGroup({
  department,
  label,
  agents,
  onSelectAgent,
}: DepartmentGroupProps) {
  const [open, setOpen] = useState(true);

  if (agents.length === 0) return null;

  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors text-left"
      >
        <div className="w-7 h-7 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center shrink-0">
          <Building2 className="w-3.5 h-3.5 text-blue-600" />
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-sm font-semibold text-slate-800">{label}</span>
          <span className="text-xs text-slate-500 ml-2">{agents.length} agents</span>
        </div>
        <ChevronDown
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${
            open ? "rotate-0" : "-rotate-90"
          }`}
        />
      </button>

      {open && (
        <div className="border-t border-slate-200 px-3 pb-3 pt-2 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {agents.map((agent) => (
            <AgentCard
              key={agent.role}
              agent={agent}
              onClick={() => onSelectAgent(agent)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
