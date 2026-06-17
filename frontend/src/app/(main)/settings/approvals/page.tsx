"use client";

import { useState } from "react";
import { Check, X, Loader2 } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getPendingApprovals, resolveApproval } from "@/lib/api";
import { useToastStore } from "@/lib/store";

export default function SettingsApprovalsPage() {
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);
  const [note, setNote] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<Record<string, boolean>>({});

  const { data, isLoading } = useQuery({
    queryKey: ["pendingApprovals"],
    queryFn: getPendingApprovals,
    refetchInterval: 30_000,
  });

  async function handleResolve(id: string, action: string) {
    setBusy((b) => ({ ...b, [id]: true }));
    try {
      await resolveApproval(id, { action: action as "approved" | "rejected", note: note[id] || "" });
      addToast(`Approval ${action}`, "success");
      queryClient.invalidateQueries({ queryKey: ["pendingApprovals"] });
    } catch (e: any) {
      addToast(e?.message || "Failed", "error");
    } finally { setBusy((b) => ({ ...b, [id]: false })); }
  }

  const pending = data ?? [];

  return (
    <div className="border-2 border-[#0A0A0A]">
      <div className="bg-[#0A0A0A] text-[#F4F4F0] px-5 py-2 flex items-center justify-between">
        <span className="font-tele text-[11px]">[ PENDING APPROVALS ]</span>
        {pending.length > 0 && <span className="font-tele text-[10px] bg-[#E61919] px-2 py-0.5">{pending.length}</span>}
      </div>
      {isLoading ? (
        <div className="p-8 text-center"><Loader2 className="w-4 h-4 text-ink/40 animate-spin mx-auto" /></div>
      ) : pending.length === 0 ? (
        <div className="p-8 text-center">
          <p className="font-tele text-[11px] text-ink/40">NO PENDING APPROVALS</p>
          <p className="font-tele text-[10px] text-ink/30 mt-1">ALL CAUGHT UP</p>
        </div>
      ) : (
        <div className="divide-y-2 divide-[#0A0A0A]">
          {pending.map((a) => (
            <div key={a.id} className="px-5 py-4 space-y-3">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-tele text-[10px] text-ink/40">{a.run_id?.slice(0, 12)}</span>
                    <span className="font-tele text-[9px] text-ink/40">/</span>
                    <span className="font-tele text-[11px] font-bold">{a.step_id}</span>
                  </div>
                  <p className="font-sans text-sm leading-relaxed text-ink/80">{a.prompt}</p>
                  {a.context && (
                    <div className="mt-2 p-3 border border-[#0A0A0A]/20 bg-[#0A0A0A]/[0.02]">
                      <p className="font-tele text-[10px] text-ink/50">CONTEXT:</p>
                      <p className="font-sans text-xs text-ink/60 mt-1 max-h-24 overflow-y-auto">{a.context}</p>
                    </div>
                  )}
                </div>
              </div>
              <textarea
                placeholder="Resolution note (optional)"
                value={note[a.id] || ""}
                onChange={(e) => setNote((n) => ({ ...n, [a.id]: e.target.value }))}
                className="w-full bg-transparent border border-[#0A0A0A]/30 px-3 py-2 text-xs font-sans text-ink/70 placeholder:text-ink/30 focus:border-[#0A0A0A] outline-none resize-none"
                rows={2}
              />
              <div className="flex gap-2">
                <button onClick={() => handleResolve(a.id, "approved")} disabled={busy[a.id]}
                  className="font-tele text-[10px] bg-[#E61919] text-[#F4F4F0] px-5 py-2 hover:bg-[#0A0A0A] transition-colors flex items-center gap-1 disabled:opacity-40">
                  {busy[a.id] ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />} APPROVE
                </button>
                <button onClick={() => handleResolve(a.id, "rejected")} disabled={busy[a.id]}
                  className="font-tele text-[10px] border-2 border-[#0A0A0A] px-5 py-2 hover:bg-[#0A0A0A] hover:text-[#F4F4F0] transition-colors flex items-center gap-1 disabled:opacity-40">
                  <X className="w-3 h-3" /> REJECT
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
