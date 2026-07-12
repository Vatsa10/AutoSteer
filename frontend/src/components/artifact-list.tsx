"use client";

import { useEffect, useState, useCallback } from "react";
import { FileText, Loader2 } from "lucide-react";
import { getArtifacts, type ArtifactSummary } from "@/lib/api";
import { ArtifactDetail } from "@/components/artifact-detail";

const badge: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600 border-slate-200",
  pending_approval: "bg-amber-50 text-amber-700 border-amber-200",
  approved: "bg-green-50 text-green-700 border-green-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
};

export function ArtifactList() {
  const [items, setItems] = useState<ArtifactSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState<string | null>(null);

  const load = useCallback(() => {
    getArtifacts().then((d) => setItems(d.artifacts)).catch(() => {}).finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const open = params.get("open");
    if (open) setOpenId(open);
  }, []);

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 text-blue-600 animate-spin" /></div>;

  return (
    <div className="max-w-3xl px-8 py-8">
      <div className="mb-6">
        <h2 className="text-base font-semibold text-slate-800 mb-1">Artifacts</h2>
        <p className="text-sm text-slate-500">Durable outputs from your runs — approve, reject, download.</p>
      </div>
      {items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-center border-2 border-dashed border-slate-200 rounded-xl">
          <FileText className="w-6 h-6 text-slate-300" />
          <p className="text-sm text-slate-400">No artifacts yet. Generate a document in chat to create one.</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {items.map((a) => (
            <button key={a.id} onClick={() => setOpenId(a.id)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-left transition-colors">
              <FileText className="w-4 h-4 text-blue-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-700 truncate">{a.title}</div>
                <div className="text-xs text-slate-400">{a.kind} · v{a.version} · {a.created_at?.slice(0, 10)}</div>
              </div>
              <span className={`text-[10px] uppercase tracking-wider border rounded px-1.5 py-0.5 shrink-0 ${badge[a.status] || badge.draft}`}>{a.status.replace("_", " ")}</span>
            </button>
          ))}
        </div>
      )}
      {openId && <ArtifactDetail id={openId} onClose={() => setOpenId(null)} onChanged={load} />}
    </div>
  );
}
