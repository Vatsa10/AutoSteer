"use client";

import ReactMarkdown from "react-markdown";
import { Loader2, Check, AlertTriangle } from "lucide-react";
import type { AgentNode } from "@/lib/store";

export function AgentBoard({ nodes }: { nodes?: AgentNode[] }) {
  if (!nodes || nodes.length === 0) return null;
  return (
    <div className="mb-3 grid grid-cols-1 md:grid-cols-2 gap-2">
      {nodes.map((n) => (
        <div key={n.id} className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-1.5 border-b border-slate-100 bg-slate-50">
            {n.status === "running" ? <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />
              : n.status === "error" ? <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
              : <Check className="w-3.5 h-3.5 text-green-600" />}
            <span className="text-xs font-medium text-slate-700 truncate">{n.agent}</span>
            {n.department && <span className="text-[10px] text-slate-400">{n.department}</span>}
            {typeof n.elapsed_ms === "number" && n.status !== "running" && (
              <span className="ml-auto text-[10px] text-slate-400">{(n.elapsed_ms / 1000).toFixed(1)}s</span>
            )}
          </div>
          <div className="px-3 py-2 text-xs text-slate-600 max-h-48 overflow-auto">
            {/* Live: show streamed tokens as they arrive; fall back to the task
                description until the first token lands. */}
            {n.status === "running" && !n.content ? (
              <span className="text-slate-400 italic">{n.description || "working…"}</span>
            ) : (
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{n.content || ""}</ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
