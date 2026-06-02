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
      className="w-full text-left bg-warm-800/40 border border-warm-700/60 rounded-lg p-3.5 hover:border-amber-700/50 hover:bg-warm-800/70 transition-all duration-150 group"
    >
      <div className="flex items-center gap-2.5 mb-2">
        <div className="w-7 h-7 rounded-md bg-amber-950/40 border border-amber-800/40 flex items-center justify-center shrink-0 transition-colors group-hover:border-amber-700/60 group-hover:bg-amber-950/60">
          <Bot className="w-3.5 h-3.5 text-amber-500" />
        </div>
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-warm-100 truncate">
            {agent.name}
          </h4>
          <p className="text-[11px] text-warm-500 font-mono truncate">
            {agent.role}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-1">
        {agent.tasks.slice(0, 4).map((task) => (
          <span
            key={task}
            className="text-[10px] bg-warm-800/80 text-warm-400 px-1.5 py-0.5 rounded-sm border border-warm-700/40"
          >
            {task.replace(/_/g, " ")}
          </span>
        ))}
        {agent.tasks.length > 4 && (
          <span className="text-[10px] text-warm-500 self-center">
            +{agent.tasks.length - 4} more
          </span>
        )}
      </div>
    </button>
  );
}
