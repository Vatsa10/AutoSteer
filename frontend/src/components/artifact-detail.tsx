"use client";

import { useEffect, useState } from "react";
import { X, Check, Ban, Download } from "lucide-react";
import { getArtifact, approveArtifact, rejectArtifact } from "@/lib/api";
import { useToastStore } from "@/lib/store";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const badge: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600 border-slate-200",
  pending_approval: "bg-amber-50 text-amber-700 border-amber-200",
  approved: "bg-green-50 text-green-700 border-green-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
};

export function ArtifactDetail({ id, onClose, onChanged }: { id: string; onClose: () => void; onChanged: () => void }) {
  const addToast = useToastStore((s) => s.addToast);
  const [data, setData] = useState<Awaited<ReturnType<typeof getArtifact>> | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => getArtifact(id).then(setData).catch(() => {});
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  async function act(kind: "approve" | "reject") {
    setBusy(true);
    try {
      if (kind === "approve") await approveArtifact(id); else await rejectArtifact(id);
      addToast(`Artifact ${kind}d`, "success");
      await load(); onChanged();
    } catch (e) { addToast(e instanceof Error ? e.message : "Failed", "error"); }
    finally { setBusy(false); }
  }

  if (!data) return null;
  const a = data.artifact;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl border border-slate-200 max-w-2xl w-full max-h-[85vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-800">{a.title}</h3>
            <span className={`text-[10px] uppercase tracking-wider border rounded px-1.5 py-0.5 ${badge[a.status] || badge.draft}`}>{a.status.replace("_", " ")}</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-5 space-y-4">
          {a.filename && (
            <a href={`${API}/api/files/download/${a.filename}`} className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700">
              <Download className="w-3.5 h-3.5" /> {a.filename}
            </a>
          )}
          {a.content && (
            <pre className="text-xs text-slate-700 whitespace-pre-wrap bg-slate-50 border border-slate-200 rounded-lg p-3 max-h-64 overflow-auto">{a.content}</pre>
          )}
          <div>
            <div className="text-[11px] uppercase tracking-wider text-slate-400 mb-1">Versions</div>
            <div className="space-y-1">
              {data.versions.map((v) => (
                <div key={v.id} className="flex items-center gap-2 text-xs text-slate-600">
                  <span className="font-medium">v{v.version}</span>
                  <span className={`text-[10px] border rounded px-1 ${badge[v.status] || badge.draft}`}>{v.status.replace("_", " ")}</span>
                  <span className="text-slate-400">{v.created_at?.slice(0, 19).replace("T", " ")}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-slate-200 px-5 py-3">
          <button disabled={busy} onClick={() => act("reject")} className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-200 text-red-600 hover:bg-red-50 disabled:opacity-50"><Ban className="w-3.5 h-3.5" /> Reject</button>
          <button disabled={busy} onClick={() => act("approve")} className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-green-600 text-white hover:bg-green-500 disabled:opacity-50"><Check className="w-3.5 h-3.5" /> Approve</button>
        </div>
      </div>
    </div>
  );
}
