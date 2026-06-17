"use client";

import { ArrowRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { getWorkflows } from "@/lib/api";

export function WorkflowList() {
  const router = useRouter();
  const { data, isLoading } = useQuery({ queryKey: ["workflows"], queryFn: getWorkflows });

  if (isLoading) {
    return <p className="font-tele text-[11px] text-ink/50 py-8">LOADING...</p>;
  }

  const workflows = data ?? [];

  return (
    <div className="border-2 border-[#0A0A0A]">
      {/* Header */}
      <div className="bg-[#0A0A0A] text-[#F4F4F0] px-5 py-2 flex items-center justify-between">
        <span className="font-tele text-[11px]">[ WORKFLOW DEFINITIONS ]</span>
        <span className="font-tele text-[10px] text-[#F4F4F0]/60">{workflows.length} DEFINED</span>
      </div>

      {workflows.length === 0 ? (
        <div className="p-8 text-center">
          <p className="font-tele text-[11px] text-ink/40">NO WORKFLOWS DEFINED</p>
          <p className="font-tele text-[10px] text-ink/30 mt-1">ADD YAML FILES TO backend/src/workflows/</p>
        </div>
      ) : (
        <div className="divide-y-2 divide-[#0A0A0A]">
          {workflows.map((wf) => (
            <div
              key={wf.name}
              className="flex items-center justify-between px-5 py-4 hover:bg-[#0A0A0A]/[0.02] transition-colors"
            >
              <div className="flex-1 min-w-0">
                <p className="font-tele text-xs text-[#0A0A0A] font-bold">{wf.name}</p>
                <p className="font-tele text-[10px] text-ink/50 mt-0.5 truncate">
                  {wf.description || "No description"}
                </p>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <span className="font-tele text-[10px] text-ink/40">{wf.step_count} STEPS</span>
                <button
                  onClick={() => router.push(`/settings/workflows/${encodeURIComponent(wf.name)}`)}
                  className="font-tele text-[10px] hover:text-[#E61919] transition-colors flex items-center gap-1"
                >
                  VIEW <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
