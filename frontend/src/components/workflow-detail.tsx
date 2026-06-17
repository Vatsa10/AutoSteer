"use client";

import { ArrowLeft, Plus } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { getWorkflowRuns, getWorkflow } from "@/lib/api";

interface Props {
  name: string;
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "completed" ? "text-[#166534]" :
    status === "failed" ? "text-[#E61919]" :
    status === "running" ? "text-[#0A0A0A]" :
    "text-ink/40";
  return <span className={`font-tele text-[10px] ${color}`}>[ {status.toUpperCase()} ]</span>;
}

export function WorkflowDetail({ name }: Props) {
  const router = useRouter();
  const { data: wf } = useQuery({
    queryKey: ["workflow", name],
    queryFn: () => getWorkflow(name),
  });
  const { data: runsResp } = useQuery({
    queryKey: ["workflowRuns", name],
    queryFn: () => getWorkflowRuns(name),
  });

  const runs = runsResp?.runs ?? [];

  return (
    <div className="space-y-8">
      {/* Back */}
      <button
        onClick={() => router.push("/settings/workflows")}
        className="font-tele text-[11px] hover:text-[#E61919] transition-colors flex items-center gap-1"
      >
        <ArrowLeft className="w-3 h-3" /> BACK TO WORKFLOWS
      </button>

      {/* Title */}
      {wf && (
        <>
          <div>
            <p className="font-tele text-[11px] text-[#E61919] mb-2">[ WORKFLOW ]</p>
            <h2 className="font-display text-3xl md:text-5xl">{wf.name}</h2>
            <p className="font-tele text-[11px] text-ink/50 mt-1">{wf.description}</p>
          </div>

          {/* Definition — step DAG */}
          <div className="border-2 border-[#0A0A0A]">
            <div className="bg-[#0A0A0A] text-[#F4F4F0] px-5 py-2">
              <span className="font-tele text-[11px]">[ DEFINITION / {wf.steps?.length ?? 0} STEPS ]</span>
            </div>
            <div className="divide-y-2 divide-[#0A0A0A]">
              {(wf.steps ?? []).map((step: any, i: number) => (
                <div key={step.id} className="px-5 py-3">
                  <div className="flex items-center gap-3">
                    <span className="font-tele text-[10px] text-ink/40 w-4">{i + 1}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-tele text-xs font-bold">{step.id}</span>
                        <span className="font-tele text-[9px] text-ink/40">[{step.type}]</span>
                      </div>
                      <p className="font-tele text-[10px] text-ink/50 mt-0.5">{step.description}</p>
                      {step.dependencies.length > 0 && (
                        <p className="font-tele text-[9px] text-ink/40 mt-1">
                          DEPENDS ON: {step.dependencies.join(" · ")}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Execution history */}
      <div className="border-2 border-[#0A0A0A]">
        <div className="bg-[#0A0A0A] text-[#F4F4F0] px-5 py-2 flex items-center justify-between">
          <span className="font-tele text-[11px]">[ EXECUTION HISTORY ]</span>
          <span className="font-tele text-[10px] text-[#F4F4F0]/60">{runs.length} RUNS</span>
        </div>
        {runs.length === 0 ? (
          <div className="p-8 text-center">
            <p className="font-tele text-[11px] text-ink/40">NO EXECUTIONS YET</p>
          </div>
        ) : (
          <div className="divide-y-2 divide-[#0A0A0A]">
            {runs.map((r: any) => (
              <div key={r.id} className="px-5 py-3 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-tele text-[10px] text-ink/40">{r.id.slice(0, 12)}</span>
                    <StatusBadge status={r.status} />
                  </div>
                  <p className="font-tele text-[9px] text-ink/40 mt-0.5">
                    {r.created_at ? new Date(r.created_at).toLocaleString() : "—"}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
