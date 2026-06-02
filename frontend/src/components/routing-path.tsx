"use client";

import { ChevronRight, User, Network, Building2, Bot } from "lucide-react";

interface RoutingPathProps {
  department: string | null;
  agent: string | null;
  compact?: boolean;
}

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

function formatAgent(role: string): string {
  return role
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace("Ai ", "AI ")
    .replace("Ml ", "ML ")
    .replace("Vp ", "VP ")
    .replace("Ceo ", "CEO ")
    .replace("Cto ", "CTO ");
}

const stepStyle =
  "flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-md border transition-all duration-300";

export function RoutingPath({ department, agent, compact = false }: RoutingPathProps) {
  if (!department && !agent) return null;

  if (compact) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-warm-400 flex-wrap">
        <User className="w-3 h-3" />
        <ChevronRight className="w-3 h-3 text-warm-600" />
        <Network className="w-3 h-3 text-amber-500" />
        <span className="text-amber-400">Master</span>
        {department && (
          <>
            <ChevronRight className="w-3 h-3 text-warm-600" />
            <Building2 className="w-3 h-3 text-amber-500" />
            <span className="text-amber-400">{formatDept(department)}</span>
          </>
        )}
        {agent && (
          <>
            <ChevronRight className="w-3 h-3 text-warm-600" />
            <Bot className="w-3 h-3 text-amber-500" />
            <span className="text-amber-300">{formatAgent(agent)}</span>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 flex-wrap animate-trace">
      <div className={`${stepStyle} bg-warm-800/60 border-warm-700 text-warm-300`}>
        <User className="w-3.5 h-3.5" />
        <span>You</span>
      </div>

      <ChevronRight className="w-3.5 h-3.5 text-warm-600" />

      <div className={`${stepStyle} bg-amber-950/40 border-amber-800/60 text-amber-300`}>
        <Network className="w-3.5 h-3.5" />
        <span>Master Orchestrator</span>
      </div>

      {department && (
        <>
          <ChevronRight className="w-3.5 h-3.5 text-warm-600" />
          <div className={`${stepStyle} bg-amber-950/40 border-amber-800/60 text-amber-300`}>
            <Building2 className="w-3.5 h-3.5" />
            <span>{formatDept(department)}</span>
          </div>
        </>
      )}

      {agent && (
        <>
          <ChevronRight className="w-3.5 h-3.5 text-warm-600" />
          <div className={`${stepStyle} bg-amber-900/50 border-amber-700/50 text-amber-200`}>
            <Bot className="w-3.5 h-3.5" />
            <span>{formatAgent(agent)}</span>
          </div>
        </>
      )}
    </div>
  );
}
