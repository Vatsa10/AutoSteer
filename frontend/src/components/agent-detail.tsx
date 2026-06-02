"use client";

import { useEffect, useRef } from "react";
import { X, Bot, Building2, Wrench, ChevronRight } from "lucide-react";
import type { AgentInfo } from "@/lib/api";

interface AgentDetailProps {
  agent: AgentInfo;
  onClose: () => void;
}

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

export function AgentDetail({ agent, onClose }: AgentDetailProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  function handleOverlayClick(e: React.MouseEvent) {
    if (e.target === overlayRef.current) onClose();
  }

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      className="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-sm"
    >
      <div className="w-full max-w-md bg-white border-l border-slate-200 h-full overflow-y-auto animate-slide-in shadow-xl">
        <div className="sticky top-0 z-10 bg-white/95 backdrop-blur-sm border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center">
              <Bot className="w-4.5 h-4.5 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900">{agent.name}</h3>
              <p className="text-xs text-slate-500 font-mono">{agent.role}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div>
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-1.5">
              <Building2 className="w-3.5 h-3.5" />
              Department
            </div>
            <p className="text-sm text-slate-800">{formatDept(agent.department)}</p>
          </div>

          <div>
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-1.5">
              <Wrench className="w-3.5 h-3.5" />
              Tools
            </div>
            {agent.tools && agent.tools.length > 0 ? (
              <div className="space-y-1.5">
                {agent.tools.map((tool) => (
                  <div key={tool.yaml_name} className="flex items-center gap-2 text-sm">
                    <span
                      className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                        tool.status === "live"
                          ? "bg-green-500"
                          : tool.status === "beta"
                            ? "bg-amber-500"
                            : "bg-slate-300"
                      }`}
                    />
                    <span className="text-slate-700">{tool.yaml_name.replace(/_/g, " ")}</span>
                    <span className="text-xs text-slate-400 font-mono">→ {tool.canonical}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No tools configured</p>
            )}
          </div>

          <div>
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-1.5">
              <Wrench className="w-3.5 h-3.5" />
              Capabilities
            </div>
            <div className="space-y-1.5">
              {agent.tasks.map((task) => (
                <div key={task} className="flex items-center gap-2 text-sm text-slate-700">
                  <ChevronRight className="w-3 h-3 text-blue-500 shrink-0" />
                  <span className="capitalize">{task.replace(/_/g, " ")}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes slide-in {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        .animate-slide-in {
          animation: slide-in 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
      `}</style>
    </div>
  );
}
