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
      className="fixed inset-0 z-50 flex justify-end"
    >
      <div className="w-full max-w-md bg-warm-900 border-l border-warm-700 h-full overflow-y-auto animate-slide-in">
        <div className="sticky top-0 z-10 bg-warm-900/95 backdrop-blur-sm border-b border-warm-800 px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-amber-950/50 border border-amber-800/50 flex items-center justify-center">
              <Bot className="w-4.5 h-4.5 text-amber-400" />
            </div>
            <div>
              <h3 className="font-semibold text-warm-100">{agent.name}</h3>
              <p className="text-xs text-warm-400 font-mono">{agent.role}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-warm-400 hover:text-warm-100 hover:bg-warm-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div>
            <div className="flex items-center gap-2 text-xs text-warm-400 mb-1.5">
              <Building2 className="w-3.5 h-3.5" />
              Department
            </div>
            <p className="text-sm text-warm-200">{formatDept(agent.department)}</p>
          </div>

          <div>
            <div className="flex items-center gap-2 text-xs text-warm-400 mb-1.5">
              <Wrench className="w-3.5 h-3.5" />
              Capabilities
            </div>
            <div className="space-y-1.5">
              {agent.tasks.map((task) => (
                <div key={task} className="flex items-center gap-2 text-sm text-warm-300">
                  <ChevronRight className="w-3 h-3 text-amber-600 shrink-0" />
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
