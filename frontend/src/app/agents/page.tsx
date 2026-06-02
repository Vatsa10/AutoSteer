"use client";

import { useEffect, useState, useMemo } from "react";
import { Search, Users } from "lucide-react";
import { getAgents, getDepartments, type AgentInfo, type DepartmentInfo } from "@/lib/api";
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
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [departments, setDepartments] = useState<DepartmentInfo[]>([]);
  const [search, setSearch] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getAgents(), getDepartments()])
      .then(([a, d]) => {
        setAgents(a);
        setDepartments(d);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

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

    // First, depts from the API (preserves order)
    for (const d of departments) {
      const key = d.department.toLowerCase().replace(/ & /g, "_").replace(/ /g, "_");
      const deptAgents = grouped.get(key);
      if (deptAgents && deptAgents.length > 0) {
        seen.add(key);
        result.push({ key, label: d.name, agents: deptAgents });
      }
    }

    // Then any remaining from agents
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
            {loading ? "Loading agents…" : `${agents.length} agents`}
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
        {loading && (
          <div className="text-center text-slate-500 py-12 text-sm">Loading agents…</div>
        )}

        {!loading && orderedDepts.length === 0 && (
          <div className="text-center text-slate-500 py-12">
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
