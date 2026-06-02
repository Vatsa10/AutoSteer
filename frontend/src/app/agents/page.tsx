"use client";

import { useState, useMemo } from "react";
import { Search, Users, Loader2, AlertCircle } from "lucide-react";
import { useAgents, useDepartments } from "@/lib/hooks";
import type { AgentInfo, DepartmentInfo } from "@/lib/api";
import { DepartmentGroup } from "@/components/department-group";
import { AgentDetail } from "@/components/agent-detail";

const deptLabels: Record<string, string> = {
  engineering: "Engineering & AI Research",
  data_analytics: "Data & Analytics",
  product: "Product",
  design: "Design",
  sales: "Sales",
  marketing: "Marketing & Growth",
  customer_success: "Customer Success & Support",
  trust_safety: "Trust, Safety & Responsible AI",
  operations: "Operations & Strategy",
  people_talent: "People & Talent",
  finance_legal: "Finance & Legal",
  executive: "Executive Leadership",
};

function formatDept(key: string): string {
  return deptLabels[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function AgentsPage() {
  const [search, setSearch] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null);

  const { data: agents = [], isLoading: agentsLoading, error: agentsError } = useAgents();
  const { data: departments = [] } = useDepartments();

  const filtered = useMemo(() => {
    if (!search.trim()) return agents;
    const q = search.toLowerCase();
    return agents.filter(
      (a) =>
        a.name.toLowerCase().includes(q) ||
        a.role.toLowerCase().includes(q) ||
        a.department.toLowerCase().includes(q) ||
        a.tasks.some((t) => t.toLowerCase().includes(q)),
    );
  }, [agents, search]);

  // Group filtered agents by department
  const grouped = useMemo(() => {
    const map = new Map<string, AgentInfo[]>();
    for (const agent of filtered) {
      const existing = map.get(agent.department) ?? [];
      existing.push(agent);
      map.set(agent.department, existing);
    }
    return map;
  }, [filtered]);

  // Use department list for ordering, with fallback to agent data
  const orderedDepts = useMemo(() => {
    const seen = new Set<string>();
    const result: { key: string; label: string; agents: AgentInfo[] }[] = [];

    for (const d of departments) {
      const key = d.department.toLowerCase().replace(/ & /g, "_").replace(/ /g, "_");
      const deptAgents = grouped.get(key);
      if (deptAgents && deptAgents.length > 0) {
        seen.add(key);
        result.push({ key, label: d.name, agents: deptAgents });
      }
    }

    for (const [key, deptAgents] of grouped) {
      if (!seen.has(key) && deptAgents.length > 0) {
        result.push({ key, label: formatDept(key), agents: deptAgents });
      }
    }

    return result;
  }, [departments, grouped]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 border-b border-slate-200 px-5 py-3.5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <Users className="w-4 h-4 text-blue-600" />
          <h2 className="text-sm font-semibold text-slate-800">
            {agentsLoading ? "Loading agents…" : `${agents.length} agents`}
          </h2>
        </div>
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search agents, roles, tasks…"
            className="w-full bg-white border border-slate-300 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-400 transition-colors"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {agentsLoading && (
          <div className="flex items-center justify-center py-16 gap-2 text-slate-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Loading agents…</span>
          </div>
        )}

        {agentsError && (
          <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
            <AlertCircle className="w-8 h-8 text-red-500" />
            <div>
              <p className="text-sm text-slate-700">Failed to load agents</p>
              <p className="text-xs text-slate-400 mt-1">Check that the backend is running on port 8000.</p>
            </div>
          </div>
        )}

        {!agentsLoading && !agentsError && orderedDepts.length === 0 && (
          <div className="text-center text-slate-500 py-16">
            <p className="text-sm">No agents found{search ? ` matching "${search}"` : ""}.</p>
          </div>
        )}

        {orderedDepts.map((dept) => (
          <DepartmentGroup
            key={dept.key}
            department={dept.key}
            label={dept.label}
            agents={dept.agents}
            onSelectAgent={setSelectedAgent}
          />
        ))}
      </div>

      {/* Agent detail panel */}
      {selectedAgent && (
        <AgentDetail agent={selectedAgent} onClose={() => setSelectedAgent(null)} />
      )}
    </div>
  );
}
