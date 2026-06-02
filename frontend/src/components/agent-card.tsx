"use client";

import { Bot } from "lucide-react";
import type { AgentInfo } from "@/lib/api";

interface AgentCardProps {
  agent: AgentInfo;
  onClick?: () => void;
}

export function AgentCard({ agent, onClick }: AgentCardProps) {
  return (
    <button
      onClick={onClick}
      type="button"
      className="w-full text-left bg-white border border-slate-200 rounded-lg p-3.5 hover:border-blue-300 hover:bg-blue-50/50 transition-all duration-150 group shadow-sm"
    >
      <div className="flex items-center gap-2.5 mb-2">
        <div className="w-7 h-7 rounded-md bg-blue-50 border border-blue-200 flex items-center justify-center shrink-0 transition-colors group-hover:border-blue-300 group-hover:bg-blue-100">
          <Bot className="w-3.5 h-3.5 text-blue-600" />
        </div>
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-slate-900 truncate">
            {agent.name}
          </h4>
          <p className="text-[11px] text-slate-500 font-mono truncate">
            {agent.role}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-1">
        {agent.tasks.slice(0, 4).map((task) => (
          <span
            key={task}
            className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded-sm border border-slate-200"
          >
            {task.replace(/_/g, " ")}
          </span>
        ))}
        {agent.tasks.length > 4 && (
          <span className="text-[10px] text-slate-400 self-center">
            +{agent.tasks.length - 4} more
          </span>
        )}
      </div>
    </button>
  );
}
